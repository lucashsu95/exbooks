"""健康檢查會被部署探針頻繁呼叫，不可產生業務／稽核事件塞滿紀錄。"""

from unittest.mock import patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_check_emits_no_business_or_audit_events(client) -> None:
    with (
        patch("core.observability.business_events.emit_business_event") as biz,
        patch("core.observability.business_events.emit_audit_event") as audit,
    ):
        resp = client.get(reverse("health_check"))
    assert resp.status_code == 200
    biz.assert_not_called()
    audit.assert_not_called()
