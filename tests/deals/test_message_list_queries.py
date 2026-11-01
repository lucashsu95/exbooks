"""交易留言列表顯示他人名稱（profile.nickname）不得產生 N+1 查詢。"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tests.factories import DealFactory, DealMessageFactory

pytestmark = pytest.mark.django_db


def _count_detail_queries(client, message_count: int) -> int:
    deal = DealFactory()
    for i in range(message_count):
        sender = deal.applicant if i % 2 == 0 else deal.responder
        DealMessageFactory(deal=deal, sender=sender)
    client.force_login(deal.responder)
    url = reverse("deals:detail", kwargs={"pk": deal.pk})
    client.get(url)  # 暖機：session、快取等一次性查詢不列入比較
    with CaptureQueriesContext(connection) as ctx:
        resp = client.get(url)
    assert resp.status_code == 200
    return len(ctx.captured_queries)


def test_deal_detail_message_list_query_count_is_constant(client):
    few = _count_detail_queries(client, 2)
    many = _count_detail_queries(client, 8)
    assert many == few
