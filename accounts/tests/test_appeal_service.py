# -*- coding: utf-8 -*-
"""Appeal Service tests"""

import pytest
from django.core.exceptions import ValidationError

from accounts.models import Appeal
from accounts.services import appeal_service
from deals.models import Notification
from tests.factories import UserFactory


pytestmark = pytest.mark.django_db


LONG_DESCRIPTION = (
    "This is a test appeal description that needs to be at least 50 characters long "
    "to pass validation. We are adding more text here to ensure the length requirement is met."
)


class TestCreateAppeal:
    """Test create appeal functionality"""

    def test_create_appeal_success(self):
        """Test successful appeal creation"""
        user = UserFactory()
        appeal = appeal_service.create_appeal(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test Appeal",
            description=LONG_DESCRIPTION,
        )
        assert appeal.pk is not None
        assert appeal.user == user
        assert appeal.status == Appeal.Status.SUBMITTED

    def test_create_appeal_description_too_short(self):
        """Test description too short raises error"""
        user = UserFactory()
        with pytest.raises(ValidationError):
            appeal_service.create_appeal(
                user=user,
                appeal_type=Appeal.AppealType.OTHER,
                title="Test Appeal",
                description="Too short",
            )

    def test_create_appeal_sends_notification(self):
        """Test notification sent after appeal creation"""
        user = UserFactory()
        appeal = appeal_service.create_appeal(  # noqa: F841
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test Appeal",
            description=LONG_DESCRIPTION,
        )
        notification = Notification.objects.filter(
            recipient=user,
            notification_type=Notification.NotificationType.APPEAL_SUBMITTED,
        ).first()
        assert notification is not None


class TestSubmitForReview:
    """Test submit for review functionality"""

    def test_submit_for_review_changes_status(self):
        """Test submit for review changes status"""
        user = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test",
            description=LONG_DESCRIPTION,
        )
        updated = appeal_service.submit_for_review(appeal.id)
        assert updated.status == Appeal.Status.UNDER_REVIEW

    def test_submit_for_review_invalid_status(self):
        """Test invalid status cannot submit for review"""
        user = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test",
            description=LONG_DESCRIPTION,
            status=Appeal.Status.UNDER_REVIEW,
        )
        with pytest.raises(ValidationError):
            appeal_service.submit_for_review(appeal.id)


class TestReviewAppeal:
    """Test review appeal functionality"""

    def test_review_appeal_approve(self):
        """Test approve appeal"""
        user = UserFactory()
        reviewer = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test",
            description=LONG_DESCRIPTION,
            status=Appeal.Status.UNDER_REVIEW,
        )
        updated = appeal_service.review_appeal(
            appeal_id=appeal.id,
            reviewer=reviewer,
            decision="approve",
            notes="Approved",
        )
        assert updated.status == Appeal.Status.APPROVED
        assert updated.resolved_by == reviewer
        assert updated.resolved_at is not None

    def test_review_appeal_reject(self):
        """Test reject appeal"""
        user = UserFactory()
        reviewer = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test",
            description=LONG_DESCRIPTION,
            status=Appeal.Status.UNDER_REVIEW,
        )
        updated = appeal_service.review_appeal(
            appeal_id=appeal.id,
            reviewer=reviewer,
            decision="reject",
            notes="Rejected",
        )
        assert updated.status == Appeal.Status.REJECTED

    def test_review_appeal_sends_notification(self):
        """Test notification sent after review"""
        user = UserFactory()
        reviewer = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test Appeal",
            description=LONG_DESCRIPTION,
            status=Appeal.Status.UNDER_REVIEW,
        )
        appeal_service.review_appeal(
            appeal_id=appeal.id,
            reviewer=reviewer,
            decision="approve",
            notes="Approved",
        )
        notification = Notification.objects.filter(
            recipient=user,
            notification_type=Notification.NotificationType.APPEAL_RESOLVED,
        ).first()
        assert notification is not None


class TestGetUserAppeals:
    """Test get user appeals functionality"""

    def test_get_user_appeals_filters_by_user(self):
        """Test get user appeals filters by user"""
        user1 = UserFactory()
        user2 = UserFactory()
        Appeal.objects.create(
            user=user1,
            appeal_type=Appeal.AppealType.OTHER,
            title="Appeal 1",
            description=LONG_DESCRIPTION,
        )
        Appeal.objects.create(
            user=user2,
            appeal_type=Appeal.AppealType.OTHER,
            title="Appeal 2",
            description=LONG_DESCRIPTION,
        )
        appeals = appeal_service.get_user_appeals(user1)
        assert appeals.count() == 1
        assert appeals.first().title == "Appeal 1"

    def test_get_user_appeals_filters_by_status(self):
        """Test get user appeals filters by status"""
        user = UserFactory()
        Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Appeal 1",
            description=LONG_DESCRIPTION,
            status=Appeal.Status.SUBMITTED,
        )
        Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Appeal 2",
            description=LONG_DESCRIPTION,
            status=Appeal.Status.UNDER_REVIEW,
        )
        appeals = appeal_service.get_user_appeals(user, status=Appeal.Status.SUBMITTED)
        assert appeals.count() == 1


class TestCancelAppeal:
    """Test cancel appeal functionality"""

    def test_cancel_appeal_success(self):
        """Test cancel appeal success"""
        user = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test",
            description=LONG_DESCRIPTION,
        )
        updated = appeal_service.cancel_appeal(appeal.id, user)
        assert updated.status == Appeal.Status.CLOSED

    def test_cancel_appeal_wrong_user(self):
        """Test cannot cancel other user appeal"""
        user1 = UserFactory()
        user2 = UserFactory()
        appeal = Appeal.objects.create(
            user=user1,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test",
            description=LONG_DESCRIPTION,
        )
        with pytest.raises(ValidationError):
            appeal_service.cancel_appeal(appeal.id, user2)

    def test_cancel_appeal_invalid_status(self):
        """Test cannot cancel appeal with invalid status"""
        user = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="Test",
            description=LONG_DESCRIPTION,
            status=Appeal.Status.APPROVED,
        )
        with pytest.raises(ValidationError):
            appeal_service.cancel_appeal(appeal.id, user)
