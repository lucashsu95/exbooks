from django.conf import settings
from django.db import models
from django_fsm import FSMField, FSMModelMixin, transition

from books.models.shared_book import SharedBook
from core.models import UpdatableModel


class Deal(FSMModelMixin, UpdatableModel):
    """
    交易記錄。涵蓋 Loan、Restore、Transfer、Regress、Except 五種類別。
    每筆交易由申請者發起、回應者回應，經面交後雙方互評完成。
    """

    class DealType(models.TextChoices):
        LOAN = "LN", "借用交易"
        RESTORE = "RS", "返還交易"
        TRANSFER = "TF", "傳遞交易"
        REGRESS = "RG", "回歸交易"
        EXCEPT = "EX", "例外處理"

    class Status(models.TextChoices):
        REQUESTED = "Q", "已請求"
        RESPONDED = "P", "已回應"
        MEETED = "M", "已面交"
        DONE = "D", "已完成"
        CANCELLED = "X", "已取消"

    shared_book = models.ForeignKey(
        "books.SharedBook",
        on_delete=models.PROTECT,
        related_name="deals",
        verbose_name="交易書籍",
    )
    book_set = models.ForeignKey(
        "books.BookSet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
        verbose_name="套書",
        help_text="若為套書交易，關聯至套書",
    )
    deal_type = models.CharField(
        max_length=2,
        choices=DealType.choices,
        verbose_name="交易類別",
    )
    status = FSMField(
        max_length=1,
        choices=Status.choices,
        default=Status.REQUESTED,
        verbose_name="交易狀態",
        protected=True,  # 禁止直接賦值
    )
    previous_book_status = models.CharField(
        max_length=1,
        choices=SharedBook.Status.choices,
        blank=True,
        verbose_name="交易前書籍狀態",
        help_text="用於取消交易時恢復書籍狀態（BR-14）",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="applied_deals",
        verbose_name="申請者",
    )
    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="responded_deals",
        verbose_name="回應者",
    )
    meeting_location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="面交地點",
    )
    meeting_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="面交時間",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="到期日",
        help_text="僅 LN/TF 類型交易需要",
    )
    applicant_rated = models.BooleanField(
        default=False,
        verbose_name="申請者已評價",
    )
    responder_rated = models.BooleanField(
        default=False,
        verbose_name="回應者已評價",
    )

    class Meta:
        db_table = "exbook_deal"
        verbose_name = "交易"
        verbose_name_plural = "交易"
        indexes = [
            models.Index(fields=["applicant", "status"]),
            models.Index(fields=["responder", "status"]),
            models.Index(fields=["shared_book", "status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["-created_at"], name="idx_created_at_desc"),
        ]

    def __str__(self):
        return f"{self.get_deal_type_display()} - {self.shared_book} ({self.get_status_display()})"

    # ========================================================================
    # FSM 狀態轉換方法
    # ========================================================================

    @transition(
        field=status,
        source=Status.REQUESTED,
        target=Status.RESPONDED,
    )
    def accept(self):
        """
        回應者接受交易申請。

        狀態轉換：REQUESTED → RESPONDED
        副作用：
        - BR-15: 拒絕同一本書的其他申請
        - 更新共享書狀態為 RESERVED（預約中）
        """
        shared_book = self.shared_book

        # BR-15: 拒絕同一本書的其他申請
        auto_cancelled = list(
            Deal.objects.filter(
                shared_book=shared_book,
                status=Deal.Status.REQUESTED,
            ).exclude(pk=self.pk)
        )
        Deal.objects.filter(
            shared_book=shared_book,
            status=Deal.Status.REQUESTED,
        ).exclude(pk=self.pk).update(status=Deal.Status.CANCELLED)
        
        self._auto_cancelled_deals = auto_cancelled

        # 更新書籍狀態為 RESERVED (使用 FSM 方法)
        shared_book.reserve()
        shared_book.save()

    @transition(
        field=status,
        source=Status.REQUESTED,
        target=Status.CANCELLED,
    )
    def decline(self):
        """
        回應者拒絕交易申請。

        狀態轉換：REQUESTED → CANCELLED
        副作用（由 signal 處理）：
        - 發送拒絕通知
        """
        pass

    @transition(
        field=status,
        source=Status.REQUESTED,
        target=Status.CANCELLED,
    )
    def cancel_request(self):
        """
        申請者取消交易申請。

        狀態轉換：REQUESTED → CANCELLED
        副作用：
        - BR-14: 恢復書籍狀態
        """
        from django.utils import timezone
        from books.models.shared_book import SharedBook

        shared_book = self.shared_book
        if self.previous_book_status:
            SharedBook.objects.filter(pk=shared_book.pk).update(
                status=self.previous_book_status,
                updated_at=timezone.now()
            )

    @transition(
        field=status,
        source=Status.RESPONDED,
        target=Status.MEETED,
    )
    def complete_meeting(self):
        """
        確認面交完成。

        狀態轉換：RESPONDED → MEETED
        副作用：
        - BR-8: 變更 SharedBook.keeper
        - 書籍狀態依交易類別轉移
        - 重新計算到期日
        """
        from datetime import timedelta
        from django.utils import timezone
        
        from deals.services.deal_service import MEET_STATUS_MAP
        from books.models.shared_book import SharedBook

        shared_book = self.shared_book

        # BR-8: 變更持有人
        if self.deal_type in (Deal.DealType.LOAN, Deal.DealType.TRANSFER):
            # 從回應者(手中有書)交給申請者
            shared_book.keeper = self.applicant
        elif self.deal_type in (Deal.DealType.RESTORE, Deal.DealType.REGRESS):
            # 從申請者(手中有書)交給回應者(Owner)
            shared_book.keeper = self.responder

        # 更新書籍狀態 - 使用 FSM 方法
        new_status = MEET_STATUS_MAP.get(self.deal_type)
        if new_status:
            if new_status == SharedBook.Status.OCCUPIED:
                shared_book.mark_as_borrowed()
            elif new_status == SharedBook.Status.SUSPENDED:
                shared_book.mark_as_suspended()
            elif new_status == SharedBook.Status.EXCEPTION:
                shared_book.declare_exception()
            else:
                shared_book.status = new_status
        
        shared_book.save()

        # 重新計算到期日
        if self.deal_type in (Deal.DealType.LOAN, Deal.DealType.TRANSFER):
            self.due_date = timezone.now().date() + timedelta(
                days=shared_book.loan_duration_days
            )

    @transition(
        field=status,
        source=Status.MEETED,
        target=Status.DONE,
    )
    def complete(self):
        """
        交易完成（雙方評價後）。

        狀態轉換：MEETED → DONE
        前置條件：申請者和回應者都已評價
        副作用（由 signal 處理）：
        - 更新信用等級
        - 發送完成通知
        """
        pass

    @transition(
        field=status,
        source=[Status.REQUESTED, Status.RESPONDED, Status.MEETED],
        target=Status.DONE,
    )
    def resolve_as_exception(self):
        """
        管理員或 Owner 處置例外，將交易強制完成。

        狀態轉換：REQUESTED/RESPONDED/MEETED → DONE
        """
        pass

    @transition(
        field=status,
        source=[Status.REQUESTED, Status.RESPONDED, Status.MEETED],
        target=Status.CANCELLED,
    )
    def cancel(self):
        """
        通用取消方法。

        狀態轉換：REQUESTED/RESPONDED/MEETED → CANCELLED
        副作用：根據來源狀態恢復書籍狀態
        """
        if self.status in [self.Status.REQUESTED, self.Status.RESPONDED]:
            shared_book = self.shared_book
            if self.previous_book_status:
                shared_book.status = self.previous_book_status
                shared_book.save(update_fields=["status", "updated_at"])

    @property
    def both_parties_rated(self):
        """檢查雙方是否都已評價。"""
        return self.applicant_rated and self.responder_rated

    @property
    def can_confirm_return(self):
        """
        是否可以正常確認歸還。
        條件：雙方已評價，且為閱畢即還類型。
        """
        return self.both_parties_rated and self.shared_book.transferability == "RETURN"
