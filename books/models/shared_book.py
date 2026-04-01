from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_fsm import FSMField, FSMModelMixin, transition

from core.models import UpdatableModel


class SharedBook(FSMModelMixin, UpdatableModel):
    """
    用戶貢獻的特定書冊。
    同一本 OfficialBook 可有多個 SharedBook（不同用戶貢獻的不同冊）。
    """

    class Transferability(models.TextChoices):
        TRANSFER = "TRANSFER", "開放傳遞"
        RETURN = "RETURN", "閱畢即還"

    class Status(models.TextChoices):
        SUSPENDED = "S", "暫不開放"
        TRANSFERABLE = "T", "可移轉"
        RESTORABLE = "R", "應返還"
        RESERVED = "V", "已被預約"
        OCCUPIED = "O", "借閱中"
        EXCEPTION = "E", "例外狀況"
        LOST = "L", "已遺失"
        DESTROYED = "D", "已損毀"

    official_book = models.ForeignKey(
        "books.OfficialBook",
        on_delete=models.PROTECT,
        related_name="shared_books",
        verbose_name="官方書目",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_books",
        verbose_name="貢獻者",
    )
    keeper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="kept_books",
        verbose_name="持有者",
    )
    book_set = models.ForeignKey(
        "books.BookSet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
        verbose_name="所屬套書",
    )
    transferability = models.CharField(
        max_length=10,
        choices=Transferability.choices,
        default=Transferability.RETURN,
        verbose_name="流通性",
    )
    status = FSMField(
        max_length=1,
        choices=Status.choices,
        default=Status.SUSPENDED,
        verbose_name="狀態",
        protected=False,  # 允許直接賦值（SharedBook 狀態由 Deal signal 控制）
    )
    condition_description = models.TextField(
        blank=True,
        verbose_name="書況描述",
    )
    loan_duration_days = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name="借閱天數",
        help_text="最少 15 天，最多 90 天",
    )
    extend_duration_days = models.PositiveIntegerField(
        default=14,
        validators=[MinValueValidator(7), MaxValueValidator(30)],
        verbose_name="可延長天數",
        help_text="最少 7 天，最多 30 天",
    )
    listed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="上架時間",
    )

    class Meta:
        db_table = "exbook_shared_book"
        verbose_name = "分享書籍"
        verbose_name_plural = "分享書籍"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["keeper", "status"]),
            models.Index(fields=["-listed_at"], name="idx_listed_at_desc"),
        ]

    def __str__(self):
        return f"{self.official_book.title} (by {self.owner})"

    # ========================================================================
    # FSM 狀態轉換方法
    # ========================================================================

    @transition(
        field=status,
        source=Status.SUSPENDED,
        target=Status.TRANSFERABLE,
    )
    def list_for_transfer(self):
        """
        將書籍上架開放借閱。

        狀態轉換：SUSPENDED → TRANSFERABLE
        副作用（由 signal 處理）：
        - 記錄上架時間
        - 通知願望清單中的使用者
        """
        pass

    @transition(
        field=status,
        source=Status.TRANSFERABLE,
        target=Status.SUSPENDED,
    )
    def suspend(self):
        """
        暫停書籍借閱。

        狀態轉換：TRANSFERABLE → SUSPENDED
        """
        pass

    @transition(
        field=status,
        source=[Status.TRANSFERABLE, Status.OCCUPIED, Status.RESTORABLE],
        target=Status.EXCEPTION,
    )
    def declare_exception(self):
        """
        宣告書籍為例外狀況。

        狀態轉換：TRANSFERABLE/OCCUPIED/RESTORABLE → EXCEPTION
        """
        pass

    @transition(
        field=status,
        source=Status.EXCEPTION,
        target=Status.LOST,
    )
    def mark_as_lost(self):
        """
        標記書籍為遺失。

        狀態轉換：EXCEPTION → LOST
        """
        pass

    @transition(
        field=status,
        source=Status.EXCEPTION,
        target=Status.DESTROYED,
    )
    def mark_as_destroyed(self):
        """
        標記書籍為損毀。

        狀態轉換：EXCEPTION → DESTROYED
        """
        pass

    @transition(
        field=status,
        source=Status.EXCEPTION,
        target=Status.SUSPENDED,
    )
    def mark_as_found(self):
        """
        標記書籍為尋獲歸還。

        狀態轉換：EXCEPTION → SUSPENDED
        """
        pass

    # Deal 相關的狀態轉換（由 deal_service 的 signal 觸發）

    @transition(
        field=status,
        source=Status.TRANSFERABLE,
        target=Status.RESERVED,
    )
    def reserve(self):
        """
        預約書籍（由 Deal accept 觸發）。

        狀態轉換：TRANSFERABLE → RESERVED
        """
        pass

    @transition(
        field=status,
        source=Status.RESERVED,
        target=Status.OCCUPIED,
    )
    def mark_as_borrowed(self):
        """
        標記為借閱中（由 Deal complete_meeting 觸發，LOAN/TRANSFER 類型）。

        狀態轉換：RESERVED → OCCUPIED
        """
        pass

    @transition(
        field=status,
        source=Status.OCCUPIED,
        target=Status.RESTORABLE,
    )
    def mark_as_overdue(self):
        """
        標記為逾期應還（由排程任務觸發）。

        狀態轉換：OCCUPIED → RESTORABLE
        """
        pass

    @transition(
        field=status,
        source=Status.OCCUPIED,
        target=Status.TRANSFERABLE,
    )
    def mark_as_returned(self):
        """
        標記為已歸還（由 Deal confirm_return 觸發）。

        狀態轉換：OCCUPIED → TRANSFERABLE
        """
        pass
