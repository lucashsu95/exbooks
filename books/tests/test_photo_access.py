import pytest
from django.urls import reverse
from tests.factories import (
    UserFactory,
    DealFactory,
    BookPhotoFactory,
    SharedBookFactory,
)


@pytest.mark.django_db
class TestPhotoAccess:
    def test_unauthenticated_user_redirected(self, client):
        """未登入請求 /photos/{pk}/serve/ → 302 redirect to login"""
        photo = BookPhotoFactory(deal=DealFactory())
        url = reverse("books:serve_protected_photo", kwargs={"pk": photo.pk})
        response = client.get(url)
        assert response.status_code == 302
        assert "login" in response.url

    def test_deal_photo_accessible_by_applicant(self, client):
        """deal.applicant 可存取 → 200 + X-Accel-Redirect header"""
        applicant = UserFactory()
        deal = DealFactory(applicant=applicant)
        photo = BookPhotoFactory(deal=deal, uploader=UserFactory())

        client.force_login(applicant)
        url = reverse("books:serve_protected_photo", kwargs={"pk": photo.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "X-Accel-Redirect" in response
        assert response["X-Accel-Redirect"] == f"/internal-media/{photo.photo.name}"

    def test_deal_photo_accessible_by_responder(self, client):
        """deal.responder 可存取 → 200 + X-Accel-Redirect header"""
        responder = UserFactory()
        deal = DealFactory(responder=responder)
        photo = BookPhotoFactory(deal=deal, uploader=UserFactory())

        client.force_login(responder)
        url = reverse("books:serve_protected_photo", kwargs={"pk": photo.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "X-Accel-Redirect" in response
        assert response["X-Accel-Redirect"] == f"/internal-media/{photo.photo.name}"

    def test_deal_photo_accessible_by_uploader(self, client):
        """photo.uploader 可存取 → 200 + X-Accel-Redirect header"""
        uploader = UserFactory()
        deal = DealFactory()
        photo = BookPhotoFactory(deal=deal, uploader=uploader)

        client.force_login(uploader)
        url = reverse("books:serve_protected_photo", kwargs={"pk": photo.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "X-Accel-Redirect" in response
        assert response["X-Accel-Redirect"] == f"/internal-media/{photo.photo.name}"

    def test_deal_photo_not_accessible_by_other_user(self, client):
        """無關使用者 → 403"""
        other_user = UserFactory()
        deal = DealFactory()
        photo = BookPhotoFactory(deal=deal)

        client.force_login(other_user)
        url = reverse("books:serve_protected_photo", kwargs={"pk": photo.pk})
        response = client.get(url)

        assert response.status_code == 403

    def test_public_photo_not_found_at_protected_endpoint(self, client):
        """公開照片 (deal=NULL) 透過此 endpoint → 404"""
        photo = BookPhotoFactory(deal=None)
        user = UserFactory()
        client.force_login(user)

        url = reverse("books:serve_protected_photo", kwargs={"pk": photo.pk})
        response = client.get(url)

        assert response.status_code == 404

    def test_public_photo_still_accessible_via_media_url(self, client):
        """公開照片仍可透過原 /media/ 路徑存取"""
        photo = BookPhotoFactory(deal=None)
        assert photo.serve_url == photo.photo.url
        assert photo.serve_url.startswith("/media/")

    @pytest.mark.parametrize("who", ["owner", "keeper"])
    def test_owner_and_keeper_accessible(self, client, who):
        """交易當事人含書籍 owner / keeper（與交易詳情同一規則）→ 200"""
        owner = UserFactory()
        keeper = UserFactory()
        shared_book = SharedBookFactory(owner=owner, keeper=keeper)
        # responder 另設他人，確保 owner / keeper 都不是 applicant / responder
        deal = DealFactory(shared_book=shared_book, responder=UserFactory())
        photo = BookPhotoFactory(
            shared_book=shared_book, deal=deal, uploader=UserFactory()
        )

        client.force_login(owner if who == "owner" else keeper)
        url = reverse("books:serve_protected_photo", kwargs={"pk": photo.pk})
        response = client.get(url)

        assert response.status_code == 200
