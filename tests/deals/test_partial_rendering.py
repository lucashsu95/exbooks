"""Test isolated partial rendering without full page context."""

import pytest
from django.template.loader import render_to_string
from tests.factories import DealFactory, UserFactory


@pytest.mark.django_db
class TestPartialRendering:
    """Verify partials render with minimal context."""

    def test_deal_card_renders_with_required_context(self):
        """_deal_card.html should work with only deal and user."""
        deal = DealFactory()
        context = {
            "deal": deal,
            "user": deal.applicant,
            "current_tab": "pending",
        }
        html = render_to_string("deals/partials/_deal_card.html", context)

        # Verify essential elements present
        assert deal.shared_book.official_book.title in html
        assert "hx-boost" in html.lower()  # HTMX preserved
        assert deal.applicant.username in html or deal.responder.username in html

    def test_empty_state_renders_with_icon_and_message(self):
        """_empty_state.html should work with icon and message."""
        context = {
            "icon": "request_page",
            "message": "目前沒有待審核的交易",
        }
        html = render_to_string("deals/partials/_empty_state.html", context)

        assert "request_page" in html
        assert "目前沒有待審核的交易" in html
        assert "material-symbols-outlined" in html

    def test_participant_card_renders_without_request_object(self):
        """_participant_card.html should work without request object."""
        user = UserFactory()
        context = {
            "user": user,
            "role_label": "申請者",
        }
        html = render_to_string("deals/partials/_participant_card.html", context)

        assert user.username in html
        assert "申請者" in html

    def test_counterpart_info_shows_correct_user(self):
        """_counterpart_info.html should show opposite party based on current_user."""
        deal = DealFactory()

        # As applicant, should see responder
        context = {"deal": deal, "current_user": deal.applicant}
        html = render_to_string("deals/partials/_counterpart_info.html", context)
        assert deal.responder.username in html
        assert deal.applicant.username not in html

        # As responder, should see applicant
        context = {"deal": deal, "current_user": deal.responder}
        html = render_to_string("deals/partials/_counterpart_info.html", context)
        assert deal.applicant.username in html
        assert deal.responder.username not in html

    @pytest.mark.parametrize(
        "status,user_role,expected_buttons",
        [
            ("Q", "responder", ["接受", "拒絕"]),
            ("Q", "applicant", ["取消申請"]),
            ("P", "responder", ["查看詳情"]),
            ("M", "applicant", ["查看詳情"]),
            ("D", "applicant", ["查看詳情"]),
            ("X", "responder", ["查看詳情"]),
        ],
    )
    def test_deal_card_shows_correct_buttons(self, status, user_role, expected_buttons):
        """_deal_card.html should show correct action buttons based on status and user role."""
        deal = DealFactory(status=status)
        user = deal.responder if user_role == "responder" else deal.applicant

        context = {"deal": deal, "user": user, "current_tab": "pending"}
        html = render_to_string("deals/partials/_deal_card.html", context)

        for btn_text in expected_buttons:
            assert btn_text in html
