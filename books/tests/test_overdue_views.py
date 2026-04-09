import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from tests.factories import UserFactory, SharedBookFactory, DealFactory


@pytest.mark.django_db
class TestOverdueListView:
    def test_overdue_list_empty(self, client):
        """測試無逾期書籍時的顯示"""
        url = reverse("books:overdue_list")
        response = client.get(url)
        assert response.status_code == 200
        assert "目前沒有嚴重逾期紀錄" in response.content.decode("utf-8")

    def test_overdue_list_with_data(self, client):
        """測試有逾期書籍時的顯示"""
        # 建立逾期 10 天的交易
        owner = UserFactory()
        applicant = UserFactory()
        applicant.profile.nickname = "小明"
        applicant.profile.save()

        book = SharedBookFactory(owner=owner, status="O", transferability="RETURN")
        DealFactory(
            shared_book=book,
            applicant=applicant,
            status="M",
            due_date=timezone.now().date() - timedelta(days=10),
        )

        url = reverse("books:overdue_list")
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "小明" in content
        assert book.official_book.title in content
        assert "逾期 10 天" in content

    def test_overdue_list_filtering(self, client):
        """測試只有逾期超過 7 天的才會顯示"""
        owner = UserFactory()
        applicant = UserFactory()

        # 1. 逾期 10 天 (應該顯示)
        book1 = SharedBookFactory(owner=owner, status="O")
        DealFactory(
            shared_book=book1,
            applicant=applicant,
            status="M",
            due_date=timezone.now().date() - timedelta(days=10),
        )

        # 2. 逾期 3 天 (不應該顯示，門檻是 7 天)
        book2 = SharedBookFactory(owner=owner, status="O")
        DealFactory(
            shared_book=book2,
            applicant=applicant,
            status="M",
            due_date=timezone.now().date() - timedelta(days=3),
        )

        url = reverse("books:overdue_list")
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert book1.official_book.title in content
        assert book2.official_book.title not in content
