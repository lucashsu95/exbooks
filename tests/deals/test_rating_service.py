import pytest
from django.core.exceptions import ValidationError

from deals.models import Deal
from deals.services.rating_service import create_rating
from tests.factories import DealFactory, UserFactory


pytestmark = pytest.mark.django_db


class TestCreateRating:
    """create_rating 測試 — 涵蓋 BR-9"""

    def test_applicant_rates(self):
        deal = DealFactory(status="M")
        rating = create_rating(
            deal,
            deal.applicant,
            friendliness_score=4,
            punctuality_score=5,
            accuracy_score=3,
        )
        assert rating.rater == deal.applicant
        assert rating.ratee == deal.responder
        deal.refresh_from_db()
        assert deal.applicant_rated is True
        assert deal.responder_rated is False

    def test_responder_rates(self):
        deal = DealFactory(status="M")
        rating = create_rating(
            deal,
            deal.responder,
            friendliness_score=4,
            punctuality_score=5,
            accuracy_score=3,
        )
        assert rating.rater == deal.responder
        assert rating.ratee == deal.applicant
        deal.refresh_from_db()
        assert deal.responder_rated is True
        assert deal.applicant_rated is False

    def test_br9_both_rated_stays_meeted(self):
        """BR-9 改良：雙方評價完成後，狀態維持 M，等待歸還按鈕點擊"""
        # 使用非 LOAN 交易（如 TRANSFER）
        deal = DealFactory(status="M", deal_type=Deal.DealType.TRANSFER)
        create_rating(
            deal,
            deal.applicant,
            friendliness_score=4,
            punctuality_score=5,
            accuracy_score=3,
        )
        create_rating(
            deal,
            deal.responder,
            friendliness_score=4,
            punctuality_score=5,
            accuracy_score=3,
        )
        deal.refresh_from_db()
        # 現在邏輯：互評完不再自動變 DONE
        assert deal.status == Deal.Status.MEETED
        assert deal.applicant_rated is True
        assert deal.responder_rated is True

    def test_single_rate_stays_meeted(self):
        """僅一方評價 → 維持 M"""
        deal = DealFactory(status="M")
        create_rating(
            deal,
            deal.applicant,
            friendliness_score=4,
            punctuality_score=5,
            accuracy_score=3,
        )
        deal.refresh_from_db()
        assert deal.status == Deal.Status.MEETED

    def test_cannot_rate_twice(self):
        deal = DealFactory(status="M")
        create_rating(
            deal,
            deal.applicant,
            friendliness_score=4,
            punctuality_score=5,
            accuracy_score=3,
        )
        with pytest.raises(ValidationError, match="已經評價"):
            create_rating(
                deal,
                deal.applicant,
                friendliness_score=3,
                punctuality_score=3,
                accuracy_score=3,
            )

    def test_non_participant_raises(self):
        deal = DealFactory(status="M")
        stranger = UserFactory()
        with pytest.raises(ValidationError, match="交易雙方"):
            create_rating(
                deal,
                stranger,
                friendliness_score=4,
                punctuality_score=5,
                accuracy_score=3,
            )

    def test_non_meeted_raises(self):
        deal = DealFactory(status="Q")
        with pytest.raises(ValidationError, match="已面交"):
            create_rating(
                deal,
                deal.applicant,
                friendliness_score=4,
                punctuality_score=5,
                accuracy_score=3,
            )

    def test_done_status_allows_rating(self):
        """D 狀態仍可評價（允許後評的一方）"""
        deal = DealFactory(status="D", applicant_rated=False)
        rating = create_rating(
            deal,
            deal.applicant,
            friendliness_score=4,
            punctuality_score=5,
            accuracy_score=3,
        )
        assert rating.pk is not None

    def test_comment_optional(self):
        deal = DealFactory(status="M")
        rating = create_rating(
            deal,
            deal.applicant,
            friendliness_score=4,
            punctuality_score=5,
            accuracy_score=3,
        )
        assert rating.comment == ""

    def test_comment_saved(self):
        deal = DealFactory(status="M")
        rating = create_rating(
            deal,
            deal.applicant,
            friendliness_score=4,
            punctuality_score=5,
            accuracy_score=3,
            comment="交易愉快",
        )
        assert rating.comment == "交易愉快"
