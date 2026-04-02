"""
交易狀態轉換服務 - 專門處理交易的狀態轉換邏輯

從原始的 deal_service.py 中拆分出來，專注於狀態機轉換。
"""

from django.db import transaction
from django.utils import timezone
from django_fsm import can_proceed

from books.models import SharedBook
from deals.models import Deal
from deals.services.notification_service import (
    notify_book_overdue,
)
from core.constants import OVERDUE_THRESHOLD_DAYS
from core.exceptions import (
    StateTransitionError,
    PermissionError,
    BusinessRuleError,
)


# ============================================================================
# 配置常數（從原 deal_service.py 移動過來）
# ============================================================================

# 面交完成後書籍狀態轉移
MEET_STATUS_MAP = {
    Deal.DealType.LOAN: SharedBook.Status.OCCUPIED,  # LN 面交 → O
    Deal.DealType.TRANSFER: SharedBook.Status.OCCUPIED,  # TF 面交 → O
    Deal.DealType.RESTORE: SharedBook.Status.SUSPENDED,  # RS 面交 → S
    Deal.DealType.REGRESS: SharedBook.Status.SUSPENDED,  # RG 面交 → S
    Deal.DealType.EXCEPT: SharedBook.Status.EXCEPTION,  # EX 面交 → E
}


class DealTransitionService:
    """交易狀態轉換服務"""

    @staticmethod
    def _validate_transition_permission(deal: Deal, user) -> None:
        """
        驗證用戶是否有權執行狀態轉換

        Args:
            deal: Deal 實例
            user: 嘗試執行轉換的用戶

        Raises:
            PermissionError: 權限不足
        """
        if deal.status == Deal.Status.REQUESTED:
            # 只有回應者可以接受/拒絕申請
            if user != deal.responder:
                raise PermissionError(
                    message="只有回應者可以處理交易申請",
                    required_permission="handle_deal_request",
                )
        elif deal.status == Deal.Status.RESPONDED:
            # 只有申請者可以取消申請
            if user != deal.applicant:
                raise PermissionError(
                    message="只有申請者可以取消交易",
                    required_permission="cancel_own_deal",
                )
        elif deal.status == Deal.Status.MEETED:
            # 雙方都可以完成面交
            if user not in (deal.applicant, deal.responder):
                raise PermissionError(
                    message="只有交易雙方可以完成面交",
                    required_permission="complete_meeting",
                )
        else:
            # 其他狀態需要具體檢查
            pass

    @staticmethod
    @transaction.atomic
    def accept_deal(deal: Deal, accepted_by) -> Deal:
        """
        接受交易申請

        Args:
            deal: 要接受的交易
            accepted_by: 接受者（應為回應者）

        Returns:
            更新後的 Deal

        Raises:
            StateTransitionError: 狀態轉換失敗
            PermissionError: 權限不足
        """
        # 權限檢查
        DealTransitionService._validate_transition_permission(deal, accepted_by)

        # FSM 檢查
        if not can_proceed(deal.accept):
            raise StateTransitionError(
                message="無法接受此交易",
                current_state=deal.status,
                target_state=Deal.Status.RESPONDED,
            )

        # 執行轉換
        deal.accept()
        deal.save()

        return deal

    @staticmethod
    @transaction.atomic
    def decline_deal(deal: Deal, declined_by) -> Deal:
        """
        拒絕交易申請

        Args:
            deal: 要拒絕的交易
            declined_by: 拒絕者（應為回應者）

        Returns:
            更新後的 Deal

        Raises:
            StateTransitionError: 狀態轉換失敗
            PermissionError: 權限不足
        """
        # 權限檢查
        DealTransitionService._validate_transition_permission(deal, declined_by)

        # FSM 檢查
        if not can_proceed(deal.decline):
            raise StateTransitionError(
                message="無法拒絕此交易",
                current_state=deal.status,
                target_state=Deal.Status.CANCELLED,
            )

        # 執行轉換
        deal.decline()
        deal.save()

        return deal

    @staticmethod
    @transaction.atomic
    def cancel_deal(deal: Deal, cancelled_by) -> Deal:
        """
        取消交易

        Args:
            deal: 要取消的交易
            cancelled_by: 取消者

        Returns:
            更新後的 Deal

        Raises:
            StateTransitionError: 狀態轉換失敗
            PermissionError: 權限不足
        """
        # 權限檢查
        DealTransitionService._validate_transition_permission(deal, cancelled_by)

        # 檢查可取消的狀態
        if deal.status not in (Deal.Status.REQUESTED, Deal.Status.RESPONDED):
            raise StateTransitionError(
                message="只有申請中或已回應的交易可以取消",
                current_state=deal.status,
                target_state=Deal.Status.CANCELLED,
            )

        # FSM 檢查
        if not can_proceed(deal.cancel_request):
            raise StateTransitionError(
                message="無法取消此交易",
                current_state=deal.status,
                target_state=Deal.Status.CANCELLED,
            )

        # 執行轉換
        deal.cancel_request()
        deal.save()

        return deal

    @staticmethod
    @transaction.atomic
    def complete_meeting(deal: Deal, completed_by) -> Deal:
        """
        完成面交

        Args:
            deal: 要完成面交的交易
            completed_by: 完成者

        Returns:
            更新後的 Deal

        Raises:
            StateTransitionError: 狀態轉換失敗
            PermissionError: 權限不足
        """
        # 權限檢查
        DealTransitionService._validate_transition_permission(deal, completed_by)

        # 只能從 RESPONDED 狀態完成面交
        if deal.status != Deal.Status.RESPONDED:
            raise StateTransitionError(
                message="只有已回應的交易可以完成面交",
                current_state=deal.status,
                target_state=Deal.Status.MEETED,
            )

        # FSM 檢查
        if not can_proceed(deal.complete_meeting):
            raise StateTransitionError(
                message="無法完成面交",
                current_state=deal.status,
                target_state=Deal.Status.MEETED,
            )

        # 更新書籍狀態
        new_status = MEET_STATUS_MAP.get(deal.deal_type)
        if new_status:
            deal.shared_book.status = new_status
            deal.shared_book.save(update_fields=["status", "updated_at"])

        # 執行轉換
        deal.complete_meeting()
        deal.save()

        return deal

    @staticmethod
    @transaction.atomic
    def process_book_due(deal: Deal) -> Deal:
        """
        處理書籍到期（逾期檢查）

        Args:
            deal: 要檢查的交易

        Returns:
            更新後的 Deal

        Raises:
            StateTransitionError: 狀態轉換失敗
            BusinessRuleError: 業務規則違反
        """
        # 只能處理借閱交易
        if deal.deal_type != Deal.DealType.LOAN:
            raise BusinessRuleError(
                message="只有借閱交易需要處理到期", rule_name="loan_due_processing"
            )

        # 只能處理已面交的交易
        if deal.status != Deal.Status.MEETED:
            raise StateTransitionError(
                message="只有已面交的借閱交易可以處理到期",
                current_state=deal.status,
                target_state=Deal.Status.DONE,
            )

        # 計算是否逾期
        now = timezone.now().date()
        due_date = deal.meeting_date + timezone.timedelta(days=deal.loan_duration_days)

        # 檢查是否已逾期超過閾值
        if now > due_date:
            overdue_days = (now - due_date).days

            # 檢查是否可以轉為完成狀態
            if overdue_days >= OVERDUE_THRESHOLD_DAYS:
                if not can_proceed(deal.complete):
                    raise StateTransitionError(
                        message="無法完成逾期交易",
                        current_state=deal.status,
                        target_state=Deal.Status.DONE,
                    )

                # 更新書籍狀態為可恢復
                deal.shared_book.status = SharedBook.Status.RESTORABLE
                deal.shared_book.save(update_fields=["status", "updated_at"])

                # 執行轉換
                deal.complete()
                deal.save()

                # 發送逾期通知
                notify_book_overdue(deal, overdue_days)

        return deal

    @staticmethod
    @transaction.atomic
    def confirm_return(deal: Deal, confirmed_by) -> Deal:
        """
        確認還書（手動完成交易）

        Args:
            deal: 要確認的交易
            confirmed_by: 確認者

        Returns:
            更新後的 Deal

        Raises:
            StateTransitionError: 狀態轉換失敗
            PermissionError: 權限不足
        """
        # 權限檢查：只有回應者可以確認還書
        if confirmed_by != deal.responder:
            raise PermissionError(
                message="只有回應者可以確認還書", required_permission="confirm_return"
            )

        # 只能確認已面交的借閱交易
        if deal.status != Deal.Status.MEETED:
            raise StateTransitionError(
                message="只有已面交的交易可以確認還書",
                current_state=deal.status,
                target_state=Deal.Status.DONE,
            )

        # FSM 檢查
        if not can_proceed(deal.complete):
            raise StateTransitionError(
                message="無法完成交易",
                current_state=deal.status,
                target_state=Deal.Status.DONE,
            )

        # 更新書籍狀態為可恢復
        deal.shared_book.status = SharedBook.Status.RESTORABLE
        deal.shared_book.save(update_fields=["status", "updated_at"])

        # 執行轉換
        deal.complete()
        deal.save()

        return deal

    @staticmethod
    def can_accept_deal(deal: Deal, user) -> bool:
        """檢查用戶是否可以接受交易"""
        try:
            DealTransitionService._validate_transition_permission(deal, user)
            return can_proceed(deal.accept)
        except (PermissionError, StateTransitionError):
            return False

    @staticmethod
    def can_decline_deal(deal: Deal, user) -> bool:
        """檢查用戶是否可以拒絕交易"""
        try:
            DealTransitionService._validate_transition_permission(deal, user)
            return can_proceed(deal.decline)
        except (PermissionError, StateTransitionError):
            return False

    @staticmethod
    def can_cancel_deal(deal: Deal, user) -> bool:
        """檢查用戶是否可以取消交易"""
        try:
            DealTransitionService._validate_transition_permission(deal, user)
            return can_proceed(deal.cancel_request)
        except (PermissionError, StateTransitionError):
            return False

    @staticmethod
    def can_complete_meeting(deal: Deal, user) -> bool:
        """檢查用戶是否可以完成面交"""
        try:
            DealTransitionService._validate_transition_permission(deal, user)
            return can_proceed(deal.complete_meeting)
        except (PermissionError, StateTransitionError):
            return False
