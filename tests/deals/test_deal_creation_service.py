"""
交易建立服務測試 - 測試 DealCreationService 的所有功能
"""

import pytest
from datetime import timedelta

from django.utils import timezone

from deals.services.deal_creation_service import DealCreationService
from deals.models import Deal
from books.models import SharedBook
from tests.factories import UserFactory, SharedBookFactory


@pytest.mark.django_db
class TestDealCreationService:
    """交易建立服務測試類別"""

    def test_create_loan_deal(self):
        """測試建立借閱交易"""
        # 建立測試數據
        owner = UserFactory()
        applicant = UserFactory()
        shared_book = SharedBookFactory(
            owner=owner,
            keeper=owner,
            status=SharedBook.Status.TRANSFERABLE,
            transferability=SharedBook.Transferability.RETURN,
        )

        # 建立借閱交易
        deal = DealCreationService.create_deal(
            shared_book=shared_book,
            applicant=applicant,
            deal_type=Deal.DealType.LOAN,
            loan_duration_days=30,
        )

        # 驗證交易屬性
        assert deal.shared_book == shared_book
        assert deal.applicant == applicant
        assert deal.responder == owner  # 借閱交易的回應者是擁有者
        assert deal.deal_type == Deal.DealType.LOAN
        assert deal.due_date is not None  # 借閱交易應有到期日
        assert deal.status == Deal.Status.REQUESTED

        # 驗證書籍狀態不變（借閱請求不改變書籍狀態）
        assert shared_book.status == SharedBook.Status.TRANSFERABLE

    def test_create_transfer_deal(self):
        """測試建立轉移交易"""
        # 建立測試數據（keeper 不同於 owner）
        owner = UserFactory()
        keeper = UserFactory()
        applicant = UserFactory()
        shared_book = SharedBookFactory(
            owner=owner,
            keeper=keeper,
            status=SharedBook.Status.TRANSFERABLE,
            transferability=SharedBook.Transferability.TRANSFER,
        )

        # 建立轉移交易
        deal = DealCreationService.create_deal(
            shared_book=shared_book,
            applicant=applicant,
            deal_type=Deal.DealType.TRANSFER,
        )

        # 驗證交易屬性
        assert deal.shared_book == shared_book
        assert deal.applicant == applicant
        assert deal.responder == keeper  # 轉移交易的回應者是持有者
        assert deal.deal_type == Deal.DealType.TRANSFER
        assert deal.due_date is None  # 轉移交易無到期日
        assert deal.status == Deal.Status.REQUESTED

    def test_create_except_deal(self):
        """測試建立例外交易（書籍遺失/損壞）"""
        owner = UserFactory()
        shared_book = SharedBookFactory(
            owner=owner,
            keeper=owner,
            status=SharedBook.Status.TRANSFERABLE,  # 可流通狀態才能申請例外處置
            transferability=SharedBook.Transferability.TRANSFER,
        )

        # 建立例外交易
        deal = DealCreationService.create_deal(
            shared_book=shared_book,
            applicant=owner,  # 擁有者發起例外交易
            deal_type=Deal.DealType.EXCEPT,
        )

        assert deal.deal_type == Deal.DealType.EXCEPT
        assert deal.status == Deal.Status.REQUESTED

    def test_validate_invalid_loan_duration(self):
        """測試驗證無效的借閱天數"""
        # 天數太短
        with pytest.raises(Exception):
            DealCreationService.create_deal(
                shared_book=SharedBookFactory(),
                applicant=UserFactory(),
                deal_type=Deal.DealType.LOAN,
                loan_duration_days=5,  # 小於最小值
            )

        # 天數太長
        with pytest.raises(Exception):
            DealCreationService.create_deal(
                shared_book=SharedBookFactory(),
                applicant=UserFactory(),
                deal_type=Deal.DealType.LOAN,
                loan_duration_days=100,  # 大於最大值
            )

        # 借閱交易未提供天數
        with pytest.raises(Exception):
            DealCreationService.create_deal(
                shared_book=SharedBookFactory(),
                applicant=UserFactory(),
                deal_type=Deal.DealType.LOAN,
                loan_duration_days=None,
            )

    def test_validate_deal_type_compatibility(self):
        """測試交易類型與書籍流通性兼容性驗證"""
        # 借閱交易需要 RETURN 流通性
        shared_book = SharedBookFactory(
            transferability=SharedBook.Transferability.TRANSFER,  # 錯誤的流通性
        )

        with pytest.raises(Exception):
            DealCreationService.create_deal(
                shared_book=shared_book,
                applicant=UserFactory(),
                deal_type=Deal.DealType.LOAN,
                loan_duration_days=30,
            )

    def test_validate_book_set_compatibility(self):
        """測試套書完整性驗證"""
        # TODO: 需要 BookSetFactory 來測試套書完整性
        # 目前先跳過
        pass

    def test_validate_user_permissions(self):
        """測試用戶權限驗證"""
        shared_book = SharedBookFactory()
        applicant = shared_book.owner  # 擁有者不能申請借閱自己的書

        with pytest.raises(Exception):
            DealCreationService.create_deal(
                shared_book=shared_book,
                applicant=applicant,
                deal_type=Deal.DealType.LOAN,
                loan_duration_days=30,
            )

    def test_get_deal_type_display(self):
        """測試取得交易類型顯示名稱"""
        display_names = {
            Deal.DealType.LOAN: "借用交易",
            Deal.DealType.TRANSFER: "傳遞交易",
            Deal.DealType.RESTORE: "返還交易",
            Deal.DealType.REGRESS: "回歸交易",
            Deal.DealType.EXCEPT: "例外處理",
        }

        for deal_type, expected_display in display_names.items():
            display = DealCreationService.get_deal_type_display(deal_type)
            assert display == expected_display

    def test_transaction_rollback_on_error(self):
        """測試錯誤時的交易回滾"""
        # TODO: 需要模擬錯誤情況
        # 目前先跳過
        pass
