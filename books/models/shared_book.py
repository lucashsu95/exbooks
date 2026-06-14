# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportIncompatibleVariableOverride=false

import logging

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, FSMModelMixin, transition

from core.models import UpdatableModel

logger = logging.getLogger(__name__)


class SharedBook(FSMModelMixin, UpdatableModel):
    """
    用戶貢獻的特定書冊。
    同一本 OfficialBook 可有多個 SharedBook（不同用戶貢獻的不同冊）。
    """

    class Transferability(models.TextChoices):
        TRANSFER = "TRANSFER", _("開放傳遞")
        RETURN = "RETURN", _("閱畢即還")

    class Status(models.TextChoices):
        SUSPENDED = "S", _("暫不開放")
        TRANSFERABLE = "T", _("可移轉")
        RESTORABLE = "R", _("應返還")
        RESERVED = "V", _("已被預約")
        OCCUPIED = "O", _("借閱中")
        EXCEPTION = "E", _("例外狀況")
        LOST = "L", _("已遺失")
        DESTROYED = "D", _("已損毀")

    official_book = models.ForeignKey(
        "books.OfficialBook",
        on_delete=models.PROTECT,
        related_name="shared_books",
        verbose_name=_("官方書目"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_books",
        verbose_name=_("貢獻者"),
    )
    keeper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="kept_books",
        verbose_name=_("持有者"),
    )
    book_set = models.ForeignKey(
        "books.BookSet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
        verbose_name=_("所屬套書"),
    )
    transferability = models.CharField(
        max_length=10,
        choices=Transferability.choices,
        default=Transferability.RETURN,
        verbose_name=_("流通性"),
    )
    status = FSMField(
        max_length=1,
        choices=Status.choices,
        default=Status.SUSPENDED,
        verbose_name=_("狀態"),
        protected=True,  # 禁止直接賦值，強制使用 FSM transition
    )
    condition_description = models.TextField(
        blank=True,
        verbose_name=_("書況描述"),
    )
    loan_duration_days = models.PositiveIntegerField(
        default=30,  # pyright: ignore[reportArgumentType]
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name=_("借閱天數"),
        help_text=_("最少 15 天，最多 90 天"),
    )
    extend_duration_days = models.PositiveIntegerField(
        default=14,  # pyright: ignore[reportArgumentType]
        validators=[MinValueValidator(7), MaxValueValidator(30)],
        verbose_name=_("可延長天數"),
        help_text=_("最少 7 天，最多 30 天"),
    )
    min_trust_level = models.PositiveSmallIntegerField(
        default=0,  # pyright: ignore[reportArgumentType]
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        verbose_name=_("最低信用等級"),
        help_text=_("申請者信用等級需達 0-3，0 表示不限制"),
    )
    listed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("上架時間"),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = "exbook_shared_book"
        verbose_name = _("分享書籍")
        verbose_name_plural = _("分享書籍")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["keeper", "status"]),
            models.Index(fields=["-listed_at"], name="idx_listed_at_desc"),
            models.Index(fields=["-updated_at"], name="idx_shared_book_updated_at"),
        ]

    def __str__(self):
        return f"{self.official_book.title} (by {self.owner})"  # pyright: ignore[reportAttributeAccessIssue]

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.TRANSFERABLE,
        })

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.SUSPENDED,
        })

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.EXCEPTION,
        })

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.LOST,
        })

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.DESTROYED,
        })

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.SUSPENDED,
        })

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.RESERVED,
        })

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.OCCUPIED,
        })

    @transition(
        field=status,
        source=[Status.RESTORABLE, Status.RESERVED],
        target=Status.SUSPENDED,
    )
    def mark_as_suspended(self):
        """
        標記為暫不開放（由 RESTORE/REGRESS 會面完成觸發）。

        狀態轉換：RESTORABLE/RESERVED → SUSPENDED
        """
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.SUSPENDED,
        })

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.RESTORABLE,
        })

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
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": SharedBook.Status.TRANSFERABLE,
        })
