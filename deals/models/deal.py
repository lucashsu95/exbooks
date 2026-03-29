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
        副作用（由 signal 處理）：
        - BR-15: 取消同一冊書的其他申請
        - 更新書籍狀態為 RESERVED（V）
        - 發送通知
        """
        pass

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
        副作用（由 signal 處理）：
        - BR-14: 恢復書籍狀態
        - 發送取消通知
        """
        pass

    @transition(
        field=status,
        source=Status.RESPONDED,
        target=Status.MEETED,
    )
    def complete_meeting(self):
        """
        確認面交完成。

        狀態轉換：RESPONDED → MEETED
        副作用（由 signal 處理）：
        - BR-8: 變更 SharedBook.keeper
        - 書籍狀態依交易類別轉移
        - 重新計算到期日
        - 發送面交完成通知
        """
        pass

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
        target=Status.CANCELLED,
    )
    def cancel(self):
        """
        通用取消方法。

        狀態轉換：REQUESTED/RESPONDED/MEETED → CANCELLED
        副作用由 signal 根據來源狀態處理。
        """
        pass

    # ========================================================================
    # FSM 條件檢查方法
    # ========================================================================

    def _both_parties_rated(self):
        """檢查雙方是否都已評價。"""
        return self.applicant_rated and self.responder_rated
