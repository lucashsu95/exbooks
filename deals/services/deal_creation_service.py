"""
交易建立服務 - 專門處理交易的建立與初始驗證

遵循單一職責原則，將交易建立邏輯從龐大的 deal_service.py 中分離出來。
"""

from typing import Optional, Tuple
from django.db import transaction

from accounts.services.trust_service import get_borrowing_limits
from books.models import SharedBook, BookSet
from books.services.book_service import validate_book_set_completeness
from deals.models import Deal
from core.constants import (
    BORROWING_DAYS_DEFAULT,
    BORROWING_DAYS_MIN,
    BORROWING_DAYS_MAX,
)
from core.exceptions import ValidationError as CoreValidationError, PermissionError


# ============================================================================
# 配置常數（從原 deal_service.py 移動過來）
# ============================================================================

# 交易類別與書籍流通性的合法對應
DEAL_TYPE_TRANSFERABILITY = {
    Deal.DealType.LOAN: SharedBook.Transferability.RETURN,  # BR-3
    Deal.DealType.RESTORE: SharedBook.Transferability.RETURN,  # BR-3
    Deal.DealType.TRANSFER: SharedBook.Transferability.TRANSFER,  # BR-4
    Deal.DealType.REGRESS: SharedBook.Transferability.TRANSFER,  # BR-4
    # EX 不限流通性
}

# 交易類別與書籍狀態的合法對應
DEAL_TYPE_REQUIRED_STATUS = {
    Deal.DealType.LOAN: SharedBook.Status.TRANSFERABLE,  # BR-5
    Deal.DealType.TRANSFER: SharedBook.Status.TRANSFERABLE,  # BR-5
    Deal.DealType.RESTORE: SharedBook.Status.RESTORABLE,  # BR-6
    Deal.DealType.REGRESS: SharedBook.Status.TRANSFERABLE,  # RG 需 T 狀態
    # EX: T/O/R 皆可（在 create_deal 中特殊處理）
}


class DealCreationService:
    """交易建立服務"""

    @staticmethod
    def _get_responder(shared_book: SharedBook, deal_type: str) -> Tuple[str, str]:
        """
        根據交易類別自動判定回應者

        Args:
            shared_book: SharedBook 實例
            deal_type: 交易類型字串

        Returns:
            Tuple[用戶實例, 角色描述]

        Rules:
            LN → Owner（借出 Lend）
            RS → Owner（取回 Retrieve）
            TF → Keeper（轉出 Export）
            RG → Keeper（交回 Revert）
            EX → Owner（處置 Resolve）
        """
        if deal_type in (
            Deal.DealType.LOAN,
            Deal.DealType.RESTORE,
            Deal.DealType.EXCEPT,
        ):
            return shared_book.owner, "owner"
        else:  # TF, RG
            return shared_book.keeper, "keeper"

    @staticmethod
    def _validate_loan_duration(
        deal_type: str, loan_duration_days: Optional[int]
    ) -> int:
        """
        驗證並處理借閱天數

        Args:
            deal_type: 交易類型
            loan_duration_days: 借閱天數（可為 None）

        Returns:
            有效的借閱天數

        Raises:
            ValidationError: 借閱天數無效
        """
        # 只有借閱交易需要天數
        if deal_type != Deal.DealType.LOAN:
            if loan_duration_days is not None:
                raise CoreValidationError(
                    message="只有借閱交易需要指定借閱天數", field="loan_duration_days"
                )
            return 0

        # 借閱交易必須有借閱天數
        if loan_duration_days is None:
            return BORROWING_DAYS_DEFAULT

        # 檢查借閱天數範圍
        if not (BORROWING_DAYS_MIN <= loan_duration_days <= BORROWING_DAYS_MAX):
            raise CoreValidationError(
                message=f"借閱天數必須在 {BORROWING_DAYS_MIN} 到 {BORROWING_DAYS_MAX} 天之間",
                field="loan_duration_days",
            )

        return loan_duration_days

    @staticmethod
    def _validate_deal_type_compatibility(
        shared_book: SharedBook, deal_type: str
    ) -> None:
        """
        驗證交易類型與書籍狀態的相容性

        Args:
            shared_book: SharedBook 實例
            deal_type: 交易類型

        Raises:
            ValidationError: 不相容
        """
        # EX 特殊處理：允許 T/O/R 狀態
        if deal_type == Deal.DealType.EXCEPT:
            if shared_book.status not in [
                SharedBook.Status.TRANSFERABLE,
                SharedBook.Status.OCCUPIED,
                SharedBook.Status.RESTORABLE,
            ]:
                raise CoreValidationError(
                    message="例外處置交易只能在書籍狀態為可流通、佔用中或可恢復時申請",
                    field="deal_type",
                )
            return

        # 檢查流通性對應
        required_transferability = DEAL_TYPE_TRANSFERABILITY.get(deal_type)
        if (
            required_transferability is not None
            and shared_book.transferability != required_transferability
        ):
            raise CoreValidationError(
                message=f"此書籍的流通性為 {shared_book.get_transferability_display()}，"
                f"無法進行 {Deal.DealType(deal_type).label} 交易",
                field="deal_type",
            )

        # 檢查狀態對應
        required_status = DEAL_TYPE_REQUIRED_STATUS.get(deal_type)
        if required_status is not None and shared_book.status != required_status:
            raise CoreValidationError(
                message=f"此書籍的狀態為 {shared_book.get_status_display()}，"
                f"無法進行 {Deal.DealType(deal_type).label} 交易",
                field="deal_type",
            )

    @staticmethod
    def _validate_book_set_compatibility(
        shared_book: SharedBook, deal_type: str, book_set: Optional[BookSet]
    ) -> None:
        """
        驗證套書相容性

        Args:
            shared_book: SharedBook 實例
            deal_type: 交易類型
            book_set: BookSet 實例（可為 None）

        Raises:
            ValidationError: 套書不相容
        """
        # 套書檢查
        if shared_book.book_set:
            if deal_type in (Deal.DealType.LOAN, Deal.DealType.TRANSFER):
                # 借出/轉出時需要整套書籍
                if not book_set:
                    raise CoreValidationError(
                        message="此書籍屬於套書，請選擇要一同借出的套書",
                        field="book_set",
                    )

                # 檢查套書完整性
                try:
                    from django.core.exceptions import (
                        ValidationError as DjangoValidationError,
                    )

                    validate_book_set_completeness(book_set)
                except DjangoValidationError as e:
                    raise CoreValidationError(
                        message=e.messages[0] if hasattr(e, "messages") else str(e),
                        field="book_set",
                    )

                # 確保選擇的套書與書籍所屬套書一致
                if book_set != shared_book.book_set:
                    raise CoreValidationError(
                        message="選擇的套書與書籍所屬套書不一致", field="book_set"
                    )
            else:
                # 非借出/轉出交易，套書應為 None
                if book_set:
                    raise CoreValidationError(
                        message="非借出/轉出交易不需指定套書", field="book_set"
                    )
        else:
            # 非套書，book_set 應為 None
            if book_set:
                raise CoreValidationError(
                    message="此書籍不屬於任何套書", field="book_set"
                )

    @staticmethod
    def _validate_user_permissions(
        applicant: str, shared_book: SharedBook, deal_type: str
    ) -> None:
        """
        驗證用戶權限

        Args:
            applicant: 申請者用戶實例
            shared_book: SharedBook 實例
            deal_type: 交易類型

        Raises:
            PermissionError: 權限不足
        """
        # 不能對自己的書籍申請借閱
        if deal_type == Deal.DealType.LOAN and applicant == shared_book.owner:
            raise PermissionError(
                message="不能對自己的書籍申請借閱",
                required_permission="borrow_others_books",
            )

        # 不能對自己目前持有的書籍申請取回
        if deal_type == Deal.DealType.RESTORE and applicant == shared_book.keeper:
            raise PermissionError(
                message="不能對自己目前持有的書籍申請取回",
                required_permission="retrieve_others_books",
            )

    @staticmethod
    @transaction.atomic
    def create_deal(
        applicant,
        shared_book: SharedBook,
        deal_type: str,
        book_set: Optional[BookSet] = None,
        loan_duration_days: Optional[int] = None,
        note: Optional[str] = None,
    ) -> Deal:
        """
        建立交易

        Args:
            applicant: 申請者
            shared_book: 交易書籍
            deal_type: 交易類型（LN/RS/TF/RG/EX）
            book_set: 套書（選填，僅借出/轉出交易需要）
            loan_duration_days: 借閱天數（選填，僅借閱交易需要）
            note: 備註（選填）

        Returns:
            Deal: 建立的交易

        Raises:
            ValidationError: 輸入驗證失敗
            PermissionError: 權限檢查失敗
        """
        # 1. 基本參數驗證
        if not shared_book:
            raise CoreValidationError(message="書籍為必填", field="shared_book")

        if not deal_type:
            raise CoreValidationError(message="交易類型為必填", field="deal_type")

        # 2. 驗證借閱天數
        validated_loan_days = DealCreationService._validate_loan_duration(
            deal_type, loan_duration_days
        )

        # 3. 驗證交易類型相容性
        DealCreationService._validate_deal_type_compatibility(shared_book, deal_type)

        # 4. 驗證套書相容性
        DealCreationService._validate_book_set_compatibility(
            shared_book, deal_type, book_set
        )

        # 5. 驗證用戶權限
        DealCreationService._validate_user_permissions(
            applicant, shared_book, deal_type
        )

        # 6. 檢查信用額度（僅借閱交易）
        if deal_type == Deal.DealType.LOAN:
            borrowing_limits = get_borrowing_limits(applicant.profile.trust_level)
            max_books = borrowing_limits["max_books"]
            current_borrowing = Deal.objects.filter(
                applicant=applicant,
                deal_type=Deal.DealType.LOAN,
                status__in=[
                    Deal.Status.REQUESTED,
                    Deal.Status.RESPONDED,
                    Deal.Status.MEETED,
                ],
            ).count()

            if current_borrowing >= max_books:
                raise CoreValidationError(
                    message=f"已達借閱上限（{max_books} 本），無法再申請借閱",
                    field="applicant",
                )

        # 7. 自動決定回應者
        responder, responder_role = DealCreationService._get_responder(
            shared_book, deal_type
        )

        # 8. 建立交易
        deal_data = {
            "shared_book": shared_book,
            "applicant": applicant,
            "responder": responder,
            "deal_type": deal_type,
            "book_set": book_set,
        }

        # 僅借閱交易需要 due_date
        if deal_type == Deal.DealType.LOAN and validated_loan_days:
            from django.utils import timezone

            deal_data["due_date"] = timezone.now().date() + timezone.timedelta(
                days=validated_loan_days
            )

        deal = Deal.objects.create(**deal_data)

        return deal

    @staticmethod
    def get_deal_type_display(deal_type: str) -> str:
        """
        取得交易類型的顯示名稱

        Args:
            deal_type: 交易類型字串

        Returns:
            顯示名稱
        """
        return Deal.DealType(deal_type).label
