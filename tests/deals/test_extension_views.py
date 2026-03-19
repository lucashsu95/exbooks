"""
延長借閱 Views 測試。
"""

import pytest
from django.urls import reverse

from books.models import SharedBook
from deals.models import Deal, LoanExtension
from tests.factories import (
    DealFactory,
    LoanExtensionFactory,
    SharedBookFactory,
    UserFactory,
)


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
