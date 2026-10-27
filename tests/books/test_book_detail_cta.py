"""
book_detail CTA 區入口回歸測試（C1 同類死條件防線）。

鎖住顯示矩陣（與 service gate 對齊）：
- owner @ T+TRANSFER → 「申請回歸」（RG 嚴格子集分支必須排在 TF 之前）
- 第三人 @ T+TRANSFER → 「申請傳遞」，無 RG / EX 入口
- keeper @ T/O/R → 「申請例外處理」次要連結
- keeper @ R → 「申請返還」主 CTA
- 非持有者 → 永遠看不到 EX 入口（service 端 EX 僅限 keeper）
"""

import pytest
from django.urls import reverse

from tests.factories import SharedBookFactory, UserFactory

pytestmark = pytest.mark.django_db


def _detail_html(client, viewer, book):
    client.force_login(viewer)
    response = client.get(reverse("books:detail", kwargs={"pk": book.id}))
    assert response.status_code == 200
    return response.content.decode()


class TestBookDetailCta:
    def test_owner_sees_regress_on_transferable(self, client):
        """owner @ T+TRANSFER 看得到「申請回歸」，且不顯示「申請傳遞」"""
        owner = UserFactory()
        keeper = UserFactory()
        book = SharedBookFactory(
            owner=owner, keeper=keeper, status="T", transferability="TRANSFER"
        )
        html = _detail_html(client, owner, book)
        assert "申請回歸" in html
        assert "申請傳遞" not in html

    def test_third_party_sees_transfer_not_regress(self, client):
        """第三人 @ T+TRANSFER 看到「申請傳遞」；RG / EX 入口皆無"""
        owner = UserFactory()
        keeper = UserFactory()
        other = UserFactory()
        book = SharedBookFactory(
            owner=owner, keeper=keeper, status="T", transferability="TRANSFER"
        )
        html = _detail_html(client, other, book)
        assert "申請傳遞" in html
        assert "申請回歸" not in html
        assert "申請例外處理" not in html

    @pytest.mark.parametrize("status", ["T", "O", "R"])
    def test_keeper_sees_except_link(self, client, status):
        """keeper @ T/O/R 看得到「申請例外處理」（EX 的合法入口只在持有者支）"""
        keeper = UserFactory()
        book = SharedBookFactory(owner=UserFactory(), keeper=keeper, status=status)
        html = _detail_html(client, keeper, book)
        assert "申請例外處理" in html

    def test_keeper_sees_restore_cta_on_restorable(self, client):
        """keeper @ R 主 CTA 為「申請返還」"""
        keeper = UserFactory()
        book = SharedBookFactory(
            owner=UserFactory(), keeper=keeper, status="R", transferability="RETURN"
        )
        html = _detail_html(client, keeper, book)
        assert "申請返還" in html

    @pytest.mark.parametrize("status", ["T", "O", "R", "E", "L", "D"])
    def test_non_keeper_never_sees_except(self, client, status):
        """非持有者在任何狀態都看不到 EX 入口（舊 E/L/D 死分支已移除）"""
        keeper = UserFactory()
        other = UserFactory()
        book = SharedBookFactory(owner=UserFactory(), keeper=keeper, status=status)
        html = _detail_html(client, other, book)
        assert "申請例外處理" not in html
        assert "申請回歸" not in html
