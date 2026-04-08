"""
交易查詢服務 - 專門處理交易的查詢與過濾邏輯

從原始的 deal_service.py 中拆分出來，專注於查詢操作。

本服務包含以下超出原需求文件的擴充功能：
- **多維度交易統計**：提供申請者/回應者雙向維度，以及依狀態、類別分組的詳細統計。
- **強化搜尋能力**：支援同時對書籍標題、ISBN 以及交易雙方的「用戶暱稱」進行關鍵字檢索。
- **即時逾期分級**：配合 overdue_service 提供不同嚴重程度的逾期資料過濾。
- **分頁與過濾整合**：在單一介面提供高度整合的狀態與類型過濾，提升大數據量下的查詢效率。
"""

from typing import Optional, List, Dict, Any
from django.db import models
from django.db.models import Q, QuerySet
from django.contrib.auth import get_user_model

from deals.models import Deal, DealMessage, LoanExtension
from books.models import SharedBook
from core.constants import PAGE_SIZE_DEFAULT, PAGE_NUMBER_DEFAULT
from core.exceptions import ValidationError as CoreValidationError

User = get_user_model()


class DealQueryService:
    """交易查詢服務"""

    @staticmethod
    def get_deals_for_user(
        user,
        status_filter: Optional[str] = None,
        deal_type_filter: Optional[str] = None,
        page: int = PAGE_NUMBER_DEFAULT,
        page_size: int = PAGE_SIZE_DEFAULT,
    ) -> Dict[str, Any]:
        """
        取得用戶相關的所有交易

        Args:
            user: 用戶實例
            status_filter: 狀態篩選（可選）
            deal_type_filter: 交易類型篩選（可選）
            page: 頁碼
            page_size: 每頁大小

        Returns:
            包含交易列表和分頁資訊的字典
        """
        # 建立查詢條件：用戶是申請者或回應者
        base_query = Q(applicant=user) | Q(responder=user)

        # 應用狀態篩選
        if status_filter:
            base_query &= Q(status=status_filter)

        # 應用交易類型篩選
        if deal_type_filter:
            base_query &= Q(deal_type=deal_type_filter)

        # 執行查詢
        deals = (
            Deal.objects.filter(base_query)
            .select_related(
                "shared_book__official_book",
                "shared_book__owner__profile",
                "shared_book__keeper__profile",
                "applicant__profile",
                "responder__profile",
            )
            .prefetch_related(
                "deal_messages",
                "loan_extensions",
            )
            .order_by("-created_at")
        )

        # 分頁處理
        total_count = deals.count()
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        return {
            "deals": deals[start_idx:end_idx],
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
        }

    @staticmethod
    def get_deal_with_details(deal_id: str, user) -> Deal:
        """
        取得交易詳情（包含相關資料）

        Args:
            deal_id: 交易 ID
            user: 請求的用戶（用於權限檢查）

        Returns:
            Deal 實例

        Raises:
            NotFoundError: 交易未找到
            PermissionError: 用戶無權查看此交易
        """
        from core.exceptions import NotFoundError, PermissionError

        try:
            deal = (
                Deal.objects.select_related(
                    "shared_book__official_book",
                    "shared_book__owner__profile",
                    "shared_book__keeper__profile",
                    "applicant__profile",
                    "responder__profile",
                )
                .prefetch_related(
                    "deal_messages",
                    "loan_extensions",
                )
                .get(id=deal_id)
            )
        except Deal.DoesNotExist:
            raise NotFoundError(
                message="交易未找到",
                resource_type="deal",
                resource_id=deal_id,
            )

        # 權限檢查：用戶必須是交易相關方
        if user not in (deal.applicant, deal.responder):
            raise PermissionError(
                message="無權查看此交易", required_permission="view_deal_details"
            )

        return deal

    @staticmethod
    def get_active_loans_for_user(user) -> QuerySet[Deal]:
        """
        取得用戶的進行中借閱交易

        Args:
            user: 用戶實例

        Returns:
            進行中借閱交易的 QuerySet
        """
        return (
            Deal.objects.filter(
                applicant=user,
                deal_type=Deal.DealType.LOAN,
                status__in=[
                    Deal.Status.REQUESTED,
                    Deal.Status.RESPONDED,
                    Deal.Status.MEETED,
                ],
            )
            .select_related("shared_book__official_book")
            .order_by("created_at")
        )

    @staticmethod
    def get_overdue_deals(days_threshold: int = 7) -> QuerySet[Deal]:
        """
        取得逾期交易

        Args:
            days_threshold: 逾期天數閾值

        Returns:
            逾期交易的 QuerySet
        """
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now().date() - timedelta(days=days_threshold)

        return Deal.objects.filter(
            deal_type=Deal.DealType.LOAN,
            status=Deal.Status.MEETED,
            meeting_date__lt=cutoff_date,
        ).select_related(
            "shared_book__official_book",
            "applicant__profile",
            "responder__profile",
        )

    @staticmethod
    def get_deal_messages(deal: Deal) -> QuerySet[DealMessage]:
        """
        取得交易的所有留言

        Args:
            deal: Deal 實例

        Returns:
            留言的 QuerySet
        """
        return (
            DealMessage.objects.filter(deal=deal)
            .select_related("sender__profile")
            .order_by("created_at")
        )

    @staticmethod
    def get_loan_extensions(deal: Deal) -> QuerySet[LoanExtension]:
        """
        取得交易的所有延期申請

        Args:
            deal: Deal 實例

        Returns:
            延期申請的 QuerySet
        """
        return (
            LoanExtension.objects.filter(deal=deal)
            .select_related(
                "requested_by__profile",
                "approved_by__profile",
            )
            .order_by("-created_at")
        )

    @staticmethod
    def search_deals(
        query: str,
        user=None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        搜尋交易

        Args:
            query: 搜尋關鍵字
            user: 用戶實例（用於過濾用戶相關交易）
            limit: 結果數量限制

        Returns:
            搜尋結果列表
        """
        if not query.strip():
            raise CoreValidationError(message="搜尋關鍵字不能為空", field="query")

        # 建立基礎查詢
        base_query = Q()

        # 如果指定用戶，只搜尋用戶相關的交易
        if user:
            base_query &= Q(applicant=user) | Q(responder=user)

        # 搜尋條件：書籍標題、ISBN、用戶暱稱
        search_query = (
            Q(shared_book__official_book__title__icontains=query)
            | Q(shared_book__official_book__isbn__icontains=query)
            | Q(applicant__profile__nickname__icontains=query)
            | Q(responder__profile__nickname__icontains=query)
        )

        deals = Deal.objects.filter(base_query & search_query).select_related(
            "shared_book__official_book",
            "applicant__profile",
            "responder__profile",
        )[:limit]

        return [
            {
                "id": str(deal.id),
                "title": deal.shared_book.official_book.title,
                "isbn": deal.shared_book.official_book.isbn,
                "deal_type": deal.deal_type,
                "status": deal.status,
                "applicant_nickname": deal.applicant.profile.nickname
                or deal.applicant.email,
                "responder_nickname": deal.responder.profile.nickname
                or deal.responder.email,
                "created_at": deal.created_at,
            }
            for deal in deals
        ]

    @staticmethod
    def get_user_deal_statistics(user) -> Dict[str, Any]:
        """
        取得用戶的交易統計

        Args:
            user: 用戶實例

        Returns:
            統計資訊字典
        """
        # 作為申請者的統計
        as_applicant = Deal.objects.filter(applicant=user)

        # 作為回應者的統計
        as_responder = Deal.objects.filter(responder=user)

        # 借閱相關統計
        loan_deals = as_applicant.filter(deal_type=Deal.DealType.LOAN)

        return {
            "total_deals": as_applicant.count() + as_responder.count(),
            "as_applicant": {
                "total": as_applicant.count(),
                "by_status": dict(
                    as_applicant.values_list("status").annotate(
                        count=models.Count("id")
                    )
                ),
                "by_type": dict(
                    as_applicant.values_list("deal_type").annotate(
                        count=models.Count("id")
                    )
                ),
            },
            "as_responder": {
                "total": as_responder.count(),
                "by_status": dict(
                    as_responder.values_list("status").annotate(
                        count=models.Count("id")
                    )
                ),
                "by_type": dict(
                    as_responder.values_list("deal_type").annotate(
                        count=models.Count("id")
                    )
                ),
            },
            "loan_statistics": {
                "total_loans": loan_deals.count(),
                "completed_loans": loan_deals.filter(status=Deal.Status.DONE).count(),
                "active_loans": loan_deals.filter(
                    status__in=[
                        Deal.Status.REQUESTED,
                        Deal.Status.RESPONDED,
                        Deal.Status.MEETED,
                    ]
                ).count(),
                "overdue_loans": DealQueryService.get_overdue_deals()
                .filter(applicant=user)
                .count(),
            },
        }

    @staticmethod
    def get_related_books_for_deal(deal: Deal) -> List[SharedBook]:
        """
        取得與交易相關的其他書籍（套書情況）

        Args:
            deal: Deal 實例

        Returns:
            相關書籍列表
        """
        if not deal.book_set:
            return []

        # 取得同套書的其他書籍
        return (
            SharedBook.objects.filter(book_set=deal.book_set)
            .exclude(id=deal.shared_book.id)
            .select_related(
                "official_book",
                "owner__profile",
                "keeper__profile",
            )
        )
