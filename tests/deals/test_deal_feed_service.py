import pytest

from deals.models import Deal
from deals.services import deal_feed_service
from tests.factories import DealFactory, UserFactory


@pytest.mark.django_db
class TestDealFeedService:
    def test_tabs_classify_deals(self):
        me = UserFactory()
        other = UserFactory()

        pending = DealFactory(responder=me, status=Deal.Status.REQUESTED)
        pending_applicant = DealFactory(
            applicant=me, status=Deal.Status.REQUESTED
        )
        meeting = DealFactory(
            applicant=me, responder=other, status=Deal.Status.RESPONDED
        )
        rating = DealFactory(
            applicant=me, responder=other, status=Deal.Status.MEETED
        )
        done = DealFactory(applicant=me, responder=other, status=Deal.Status.DONE)

        pending_feed = deal_feed_service.get_feed(me, "pending")
        assert [d.pk for d in pending_feed["pending_responder"]] == [pending.pk]
        assert pending_feed["pending_responder"].count() == 1
        assert list(pending_feed["grouped_pending"].keys()) == [pending.shared_book]

        assert (
            [d.pk for d in deal_feed_service.get_feed(me, "pending_applicant")["pending_applicant"]]
            == [pending_applicant.pk]
        )
        assert (
            [d.pk for d in deal_feed_service.get_feed(me, "meeting")["pending_meeting"]]
            == [meeting.pk]
        )
        assert (
            [d.pk for d in deal_feed_service.get_feed(me, "rating")["pending_rating"]]
            == [rating.pk]
        )
        assert (
            [d.pk for d in deal_feed_service.get_feed(me, "history")["history"]]
            == [done.pk]
        )

    def test_inactive_tab_keeps_count_but_empty_items(self):
        me = UserFactory()
        DealFactory(responder=me, status=Deal.Status.REQUESTED)

        feed = deal_feed_service.get_feed(me, "meeting")
        assert list(feed["pending_responder"]) == []
        assert feed["pending_responder"].count() == 1

    def test_invalid_tab_falls_back_to_pending(self):
        me = UserFactory()
        assert deal_feed_service.get_feed(me, "bogus")["current_tab"] == "pending"

    def test_unrelated_deals_excluded(self):
        me = UserFactory()
        DealFactory()  # 與 me 無關
        assert list(deal_feed_service.get_feed(me, "pending")["deals"]) == []
