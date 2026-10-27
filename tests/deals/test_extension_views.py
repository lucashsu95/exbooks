"""
延長借閱 Views 測試。
"""

import pytest
from django.urls import reverse

from deals.forms import ExtensionRequestForm
from deals.models import LoanExtension
from tests.factories import (
    DealFactory,
    LoanExtensionFactory,
    SharedBookFactory,
    UserFactory,
)


def _detail_response(client, viewer, deal):
    client.force_login(viewer)
    return client.get(reverse("deals:detail", kwargs={"pk": deal.id}))


pytestmark = pytest.mark.django_db


class TestExtensionRequestView:
    """測試 extension_request view"""

    def test_get_form_as_applicant(self, client):
        """申請者 GET 請求應顯示表單"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )

        client.force_login(applicant)
        url = reverse("deals:extension_request", kwargs={"deal_pk": deal.id})
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context
        assert "deals/extension_request.html" in [t.name for t in response.templates]

    def test_get_as_responder_forbidden(self, client):
        """回應者 GET 請求應被拒絕"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )

        client.force_login(owner)
        url = reverse("deals:extension_request", kwargs={"deal_pk": deal.id})
        response = client.get(url)

        assert response.status_code == 302  # 重定向

    def test_post_success(self, client):
        """申請者 POST 有效資料應成功建立延長申請"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )

        client.force_login(applicant)
        url = reverse("deals:extension_request", kwargs={"deal_pk": deal.id})
        response = client.post(url, {"extra_days": 14})

        assert response.status_code == 302  # 重定向到 deal_detail
        assert LoanExtension.objects.filter(deal=deal).exists()

    def test_post_invalid_days(self, client):
        """POST 無效天數應顯示錯誤"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )

        client.force_login(applicant)
        url = reverse("deals:extension_request", kwargs={"deal_pk": deal.id})
        response = client.post(url, {"extra_days": 5})  # 小於最小值 7

        assert response.status_code == 200
        assert "form" in response.context
        assert not LoanExtension.objects.filter(deal=deal).exists()

    def test_post_non_occupied_book(self, client):
        """非借閱中狀態的書籍應顯示錯誤"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, status="T")  # 可借狀態
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )

        client.force_login(applicant)
        url = reverse("deals:extension_request", kwargs={"deal_pk": deal.id})
        response = client.post(url, {"extra_days": 14})

        # 表單驗證失敗，重新渲染頁面並顯示錯誤訊息
        assert response.status_code == 200
        assert not LoanExtension.objects.filter(deal=deal).exists()


class TestExtensionRequestForm:
    @pytest.mark.parametrize(
        ("days", "valid"),
        [(6, False), (7, True), (14, True), (30, True), (31, False), ("abc", False)],
    )
    def test_extra_days_bounds(self, days, valid):
        form = ExtensionRequestForm(data={"extra_days": days})
        assert form.is_valid() is valid


class TestExtensionApproveView:
    """測試 extension_approve view"""

    def test_post_success(self, client):
        """回應者 POST 應成功核准延長申請"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        extension = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.PENDING,
        )

        client.force_login(owner)
        url = reverse("deals:extension_approve", kwargs={"extension_pk": extension.id})
        response = client.post(url)

        assert response.status_code == 302
        extension.refresh_from_db()
        assert extension.status == LoanExtension.Status.APPROVED

    def test_post_as_applicant_forbidden(self, client):
        """申請者 POST 應被拒絕"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        extension = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.PENDING,
        )

        client.force_login(applicant)
        url = reverse("deals:extension_approve", kwargs={"extension_pk": extension.id})
        response = client.post(url)

        assert response.status_code == 302
        extension.refresh_from_db()
        assert extension.status == LoanExtension.Status.PENDING  # 未被修改

    def test_get_not_allowed(self, client):
        """GET 請求應不被允許"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        extension = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.PENDING,
        )

        client.force_login(owner)
        url = reverse("deals:extension_approve", kwargs={"extension_pk": extension.id})
        response = client.get(url)

        assert response.status_code == 405  # Method Not Allowed


class TestExtensionRejectView:
    """測試 extension_reject view"""

    def test_post_success(self, client):
        """回應者 POST 應成功拒絕延長申請"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        extension = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.PENDING,
        )

        client.force_login(owner)
        url = reverse("deals:extension_reject", kwargs={"extension_pk": extension.id})
        response = client.post(url)

        assert response.status_code == 302
        extension.refresh_from_db()
        assert extension.status == LoanExtension.Status.REJECTED

    def test_post_as_applicant_forbidden(self, client):
        """申請者 POST 應被拒絕"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        extension = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.PENDING,
        )

        client.force_login(applicant)
        url = reverse("deals:extension_reject", kwargs={"extension_pk": extension.id})
        response = client.post(url)

        assert response.status_code == 302
        extension.refresh_from_db()
        assert extension.status == LoanExtension.Status.PENDING  # 未被修改


class TestExtensionCancelView:
    """測試 extension_cancel view"""

    def test_post_success(self, client):
        """申請者 POST 應成功取消延長申請"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        extension = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.PENDING,
        )

        client.force_login(applicant)
        url = reverse("deals:extension_cancel", kwargs={"extension_pk": extension.id})
        response = client.post(url)

        assert response.status_code == 302
        extension.refresh_from_db()
        assert extension.status == LoanExtension.Status.REJECTED

    def test_post_as_responder_forbidden(self, client):
        """回應者 POST 應被拒絕"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        extension = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.PENDING,
        )

        client.force_login(owner)
        url = reverse("deals:extension_cancel", kwargs={"extension_pk": extension.id})
        response = client.post(url)

        assert response.status_code == 302
        extension.refresh_from_db()
        assert extension.status == LoanExtension.Status.PENDING  # 未被修改

    def test_post_non_pending_forbidden(self, client):
        """非 PENDING 狀態的申請無法取消"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        extension = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.APPROVED,  # 已核准
        )

        client.force_login(applicant)
        url = reverse("deals:extension_cancel", kwargs={"extension_pk": extension.id})
        response = client.post(url)

        assert response.status_code == 302
        extension.refresh_from_db()
        assert extension.status == LoanExtension.Status.APPROVED  # 未被修改


class TestDealDetailExtensionEntry:
    """deal_detail 的「新增申請」入口。

    回歸背景：模板曾以 `deal.status == 'O'`（SharedBook 的借閱中狀態碼，
    Deal 狀態為 Q/P/M/D/X）作為入口條件，永為 false，借閱者從 UI 找不到
    新增延期申請的入口。入口條件改由 extension_service.is_extension_eligible
    單一來源判定（view context 的 can_request_extension）。
    """

    def _met_loan_deal(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        return deal, applicant, owner

    def test_applicant_sees_new_request_link(self, client):
        """借閱中 + 借閱者視角 + 無 pending → 看得到「新增申請」入口。"""
        deal, applicant, _ = self._met_loan_deal()
        response = _detail_response(client, applicant, deal)

        assert response.status_code == 200
        assert "新增申請" in response.content.decode()
        expected_href = reverse(
            "deals:extension_request", kwargs={"deal_pk": deal.id}
        )
        assert f'href="{expected_href}"' in response.content.decode()
        assert response.context["can_request_extension"] is True

    def test_responder_does_not_see_link(self, client):
        """出借者視角看不到「新增申請」（資格在借閱者）。"""
        deal, _, owner = self._met_loan_deal()
        response = _detail_response(client, owner, deal)

        assert response.status_code == 200
        assert "新增申請" not in response.content.decode()
        assert response.context["can_request_extension"] is False

    def test_applicant_with_pending_sees_records_not_link(self, client):
        """已有 PENDING 記錄 → 紀錄區可見（可取消），但沒有「新增申請」連結。"""
        deal, applicant, _ = self._met_loan_deal()
        LoanExtensionFactory(deal=deal, requested_by=applicant)
        response = _detail_response(client, applicant, deal)

        assert response.status_code == 200
        assert "延期申請紀錄" in response.content.decode()
        assert "新增申請" not in response.content.decode()
        assert response.context["can_request_extension"] is False

    def test_section_visible_to_responder_with_pending(self, client):
        """出借者有 pending 記錄時看得到紀錄區（核准/拒絕入口在記錄卡上）。"""
        deal, applicant, owner = self._met_loan_deal()
        LoanExtensionFactory(deal=deal, requested_by=applicant)
        response = _detail_response(client, owner, deal)

        assert response.status_code == 200
        assert "延期申請紀錄" in response.content.decode()
        assert "新增申請" not in response.content.decode()

    def test_no_section_when_nothing_to_show(self, client):
        """書未借閱中（Q 階段）且無紀錄 → 整段延期區塊不顯示。"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, status="T")
        deal = DealFactory(
            shared_book=book,
            status="Q",
            applicant=applicant,
            responder=owner,
        )
        response = _detail_response(client, applicant, deal)

        assert response.status_code == 200
        assert "延期申請紀錄" not in response.content.decode()
        assert response.context["can_request_extension"] is False
