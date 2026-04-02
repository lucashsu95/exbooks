from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from books.models import SharedBook
from deals.models import Deal, Notification
from deals.services.deal_service import (
    accept_deal,
    cancel_deal,
    complete_meeting,
    create_deal,
    decline_deal,
    process_book_due,
)
from tests.factories import (
    BookSetFactory,
    DealFactory,
    SharedBookFactory,
    UserFactory,
)


pytestmark = pytest.mark.django_db


# ============================================================
# create_deal — BR-3, BR-4, BR-5, BR-6, BR-7, BR-10
# ============================================================
class TestCreateDeal:
    # --- Happy paths ---

    def test_loan_success(self):
        """LN: RETURN 流通性 + T 狀態 → 成功建立"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            status="T",
            transferability="RETURN",
            loan_duration_days=30,
        )
        deal = create_deal(applicant, book, Deal.DealType.LOAN)
        assert deal.deal_type == Deal.DealType.LOAN
        assert deal.status == Deal.Status.REQUESTED
        assert deal.applicant == applicant
        assert deal.responder == owner  # LN → Owner
        assert deal.previous_book_status == "T"
        assert deal.due_date == timezone.now().date() + timedelta(days=30)

    def test_loan_with_note_success(self):
        """建立交易時填寫備註 → 成功建立並存為 DealMessage"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            status="T",
            transferability="RETURN",
        )
        note_content = "我想在捷運站面交"
        deal = create_deal(applicant, book, Deal.DealType.LOAN, note=note_content)

        assert deal.messages.count() == 1
        message = deal.messages.first()
        assert message.sender == applicant
        assert message.content == note_content

    def test_transfer_success(self):
        """TF: TRANSFER 流通性 + T 狀態 → responder 為 Keeper"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            status="T",
            transferability="TRANSFER",
        )
        deal = create_deal(applicant, book, Deal.DealType.TRANSFER)
        assert deal.deal_type == Deal.DealType.TRANSFER
        assert deal.responder == book.keeper

    def test_restore_success(self):
        """RS: RETURN 流通性 + R 狀態 → responder 為 Owner"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            status="R",
            transferability="RETURN",
        )
        deal = create_deal(applicant, book, Deal.DealType.RESTORE)
        assert deal.deal_type == Deal.DealType.RESTORE
        assert deal.responder == owner
        assert deal.due_date is None  # RS 不設到期日

    def test_regress_success(self):
        """RG: Owner 發起, responder=Keeper"""
        keeper = UserFactory()
        owner = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            keeper=keeper,
            status="T",
            transferability="TRANSFER",
        )
        deal = create_deal(owner, book, Deal.DealType.REGRESS)
        assert deal.responder == keeper

    @pytest.mark.parametrize("status", ["T", "O", "R"])
    def test_except_valid_statuses(self, status):
        """EX: T/O/R 皆可"""
        applicant = UserFactory()
        book = SharedBookFactory(status=status)
        deal = create_deal(applicant, book, Deal.DealType.EXCEPT)
        assert deal.deal_type == Deal.DealType.EXCEPT

    # --- BR-3: LN/RS 僅適用 RETURN ---

    def test_br3_loan_requires_return(self):
        applicant = UserFactory()
        book = SharedBookFactory(status="T", transferability="TRANSFER")
        with pytest.raises(ValidationError, match="閱畢即還"):
            create_deal(applicant, book, Deal.DealType.LOAN)

    def test_br3_restore_requires_return(self):
        applicant = UserFactory()
        book = SharedBookFactory(status="R", transferability="TRANSFER")
        with pytest.raises(ValidationError, match="閱畢即還"):
            create_deal(applicant, book, Deal.DealType.RESTORE)

    # --- BR-4: TF/RG 僅適用 TRANSFER ---

    def test_br4_transfer_requires_transfer(self):
        applicant = UserFactory()
        book = SharedBookFactory(status="T", transferability="RETURN")
        with pytest.raises(ValidationError, match="開放傳遞"):
            create_deal(applicant, book, Deal.DealType.TRANSFER)

    def test_br4_regress_requires_transfer(self):
        owner = UserFactory()
        book = SharedBookFactory(owner=owner, status="T", transferability="RETURN")
        with pytest.raises(ValidationError, match="開放傳遞"):
            create_deal(owner, book, Deal.DealType.REGRESS)

    # --- BR-5: LN/TF 需書籍狀態 T ---

    def test_br5_loan_requires_transferable(self):
        applicant = UserFactory()
        book = SharedBookFactory(status="S", transferability="RETURN")
        with pytest.raises(ValidationError, match="可移轉"):
            create_deal(applicant, book, Deal.DealType.LOAN)

    def test_br5_transfer_requires_transferable(self):
        applicant = UserFactory()
        book = SharedBookFactory(status="S", transferability="TRANSFER")
        with pytest.raises(ValidationError, match="可移轉"):
            create_deal(applicant, book, Deal.DealType.TRANSFER)

    # --- BR-6: RS 需書籍狀態 R ---

    def test_br6_restore_requires_restorable(self):
        applicant = UserFactory()
        book = SharedBookFactory(status="T", transferability="RETURN")
        with pytest.raises(ValidationError, match="應返還"):
            create_deal(applicant, book, Deal.DealType.RESTORE)

    # --- BR-7: 套書完整性 ---

    def test_br7_book_set_incomplete_raises(self):
        applicant = UserFactory()
        owner = UserFactory()
        book_set = BookSetFactory(owner=owner)
        book1 = SharedBookFactory(
            owner=owner,
            status="T",
            transferability="RETURN",
            book_set=book_set,
        )
        SharedBookFactory(
            owner=owner,
            status="S",
            transferability="RETURN",
            book_set=book_set,
        )
        with pytest.raises(ValidationError, match="無法借出"):
            create_deal(applicant, book1, Deal.DealType.LOAN)

    # --- BR-10: 不能借閱自己的書 ---

    def test_br10_owner_cannot_borrow_own(self):
        owner = UserFactory()
        book = SharedBookFactory(owner=owner, status="T", transferability="RETURN")
        with pytest.raises(ValidationError, match="自己"):
            create_deal(owner, book, Deal.DealType.LOAN)

    def test_br10_keeper_cannot_borrow_kept(self):
        keeper = UserFactory()
        book = SharedBookFactory(keeper=keeper, status="T", transferability="RETURN")
        with pytest.raises(ValidationError, match="自己"):
            create_deal(keeper, book, Deal.DealType.LOAN)

    def test_br10_regress_exempt(self):
        """RG 不受 BR-10 限制（Owner 可對自己的書發起）"""
        owner = UserFactory()
        keeper = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            keeper=keeper,
            status="T",
            transferability="TRANSFER",
        )
        deal = create_deal(owner, book, Deal.DealType.REGRESS)
        assert deal.applicant == owner

    # --- EX 狀態限制 ---

    @pytest.mark.parametrize("status", ["S", "V", "E", "L", "D"])
    def test_except_invalid_statuses_raise(self, status):
        applicant = UserFactory()
        book = SharedBookFactory(status=status)
        with pytest.raises(ValidationError):
            create_deal(applicant, book, Deal.DealType.EXCEPT)

    # --- 通知 ---

    def test_notification_sent_to_responder(self):
        applicant = UserFactory()
        book = SharedBookFactory(status="T", transferability="RETURN")
        create_deal(applicant, book, Deal.DealType.LOAN)
        assert Notification.objects.filter(
            recipient=book.owner,
            notification_type="DEAL_REQUESTED",
        ).exists()


# ============================================================
# accept_deal — BR-15
# ============================================================
class TestAcceptDeal:
    def test_status_transition(self):
        """Q → P, 書籍 → V"""
        book = SharedBookFactory(status="T", transferability="RETURN")
        deal = DealFactory(shared_book=book, status="Q")
        accept_deal(deal)
        deal.refresh_from_db()
        book.refresh_from_db()
        assert deal.status == Deal.Status.RESPONDED
        assert book.status == SharedBook.Status.RESERVED

    def test_non_requested_raises(self):
        deal = DealFactory(status="P")
        with pytest.raises(ValidationError, match="已請求"):
            accept_deal(deal)

    def test_br15_auto_cancel_others(self):
        """接受後同書其餘 Q 申請自動取消"""
        book = SharedBookFactory(status="T", transferability="RETURN")
        deal1 = DealFactory(shared_book=book, status="Q")
        deal2 = DealFactory(shared_book=book, status="Q")
        deal3 = DealFactory(shared_book=book, status="Q")
        accept_deal(deal1)
        deal2.refresh_from_db()
        deal3.refresh_from_db()
        assert deal2.status == Deal.Status.CANCELLED
        assert deal3.status == Deal.Status.CANCELLED

    def test_br15_cancelled_deals_notified(self):
        """被自動取消的申請者收到通知"""
        book = SharedBookFactory(status="T", transferability="RETURN")
        deal1 = DealFactory(shared_book=book, status="Q")
        deal2 = DealFactory(shared_book=book, status="Q")
        accept_deal(deal1)
        assert Notification.objects.filter(
            recipient=deal2.applicant,
            notification_type="DEAL_CANCELLED",
        ).exists()

    def test_notification_sent_to_applicant(self):
        book = SharedBookFactory(status="T", transferability="RETURN")
        deal = DealFactory(shared_book=book, status="Q")
        accept_deal(deal)
        assert Notification.objects.filter(
            recipient=deal.applicant,
            notification_type="DEAL_RESPONDED",
        ).exists()


# ============================================================
# decline_deal
# ============================================================
class TestDeclineDeal:
    def test_status_transition(self):
        deal = DealFactory(status="Q")
        decline_deal(deal)
        deal.refresh_from_db()
        assert deal.status == Deal.Status.CANCELLED

    def test_non_requested_raises(self):
        deal = DealFactory(status="P")
        with pytest.raises(ValidationError, match="已請求"):
            decline_deal(deal)

    def test_notification_sent_to_applicant(self):
        deal = DealFactory(status="Q")
        decline_deal(deal)
        assert Notification.objects.filter(
            recipient=deal.applicant,
            notification_type="DEAL_CANCELLED",
        ).exists()


# ============================================================
# cancel_deal — BR-13, BR-14
# ============================================================
class TestCancelDeal:
    def test_br13_cancel_from_requested(self):
        deal = DealFactory(status="Q")
        cancel_deal(deal)
        deal.refresh_from_db()
        assert deal.status == Deal.Status.CANCELLED

    def test_non_requested_raises(self):
        deal = DealFactory(status="P")
        with pytest.raises(ValidationError, match="已請求"):
            cancel_deal(deal)

    def test_br14_restore_book_status(self):
        """取消後書籍狀態恢復"""
        book = SharedBookFactory(status="T", transferability="RETURN")
        deal = DealFactory(
            shared_book=book,
            status="Q",
            previous_book_status="T",
        )
        book.status = "V"
        book.save(update_fields=["status"])
        cancel_deal(deal)
        book.refresh_from_db()
        assert book.status == "T"

    def test_notification_sent_to_responder(self):
        deal = DealFactory(status="Q")
        cancel_deal(deal)
        assert Notification.objects.filter(
            recipient=deal.responder,
            notification_type="DEAL_CANCELLED",
        ).exists()


# ============================================================
# complete_meeting — BR-8
# ============================================================
class TestCompleteMeeting:
    def test_loan_meeting(self):
        """LN: P→M, keeper→applicant, book→O, 到期日重算"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            keeper=owner,
            status="V",
            transferability="RETURN",
            loan_duration_days=30,
        )
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="P",
            applicant=applicant,
            responder=owner,
        )
        complete_meeting(deal)
        deal.refresh_from_db()
        book.refresh_from_db()
        assert deal.status == Deal.Status.MEETED
        assert book.keeper == applicant
        assert book.status == SharedBook.Status.OCCUPIED
        assert deal.due_date == timezone.now().date() + timedelta(days=30)

    def test_transfer_meeting(self):
        """TF: keeper→applicant, book→O"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            keeper=owner,
            status="V",
            transferability="TRANSFER",
            loan_duration_days=30,
        )
        deal = DealFactory(
            shared_book=book,
            deal_type="TF",
            status="P",
            applicant=applicant,
            responder=owner,
        )
        complete_meeting(deal)
        book.refresh_from_db()
        assert book.keeper == applicant
        assert book.status == SharedBook.Status.OCCUPIED

    def test_restore_meeting(self):
        """RS: keeper→responder(owner), book→S"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            keeper=applicant,
            status="V",
            transferability="RETURN",
        )
        deal = DealFactory(
            shared_book=book,
            deal_type="RS",
            status="P",
            applicant=applicant,
            responder=owner,
        )
        complete_meeting(deal)
        book.refresh_from_db()
        assert book.keeper == owner
        assert book.status == SharedBook.Status.SUSPENDED

    def test_non_responded_raises(self):
        deal = DealFactory(status="Q")
        with pytest.raises(ValidationError, match="已回應"):
            complete_meeting(deal)

    def test_notification_both_parties(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            keeper=owner,
            status="V",
            transferability="RETURN",
            loan_duration_days=30,
        )
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="P",
            applicant=applicant,
            responder=owner,
        )
        complete_meeting(deal)
        meeted_notifs = Notification.objects.filter(
            notification_type="DEAL_MEETED",
        )
        assert meeted_notifs.count() == 2


# ============================================================
# process_book_due — BR-12
# ============================================================
class TestProcessBookDue:
    def test_return_book_overdue(self):
        """閱畢即還到期 → R"""
        book = SharedBookFactory(status="O", transferability="RETURN")
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="M",
            due_date=timezone.now().date() - timedelta(days=1),
        )
        process_book_due(deal)
        book.refresh_from_db()
        assert book.status == SharedBook.Status.RESTORABLE

    def test_transfer_book_overdue(self):
        """開放傳遞到期 → T"""
        book = SharedBookFactory(status="O", transferability="TRANSFER")
        deal = DealFactory(
            shared_book=book,
            deal_type="TF",
            status="M",
            due_date=timezone.now().date() - timedelta(days=1),
        )
        process_book_due(deal)
        book.refresh_from_db()
        assert book.status == SharedBook.Status.TRANSFERABLE

    def test_not_due_yet_no_change(self):
        book = SharedBookFactory(status="O", transferability="RETURN")
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="M",
            due_date=timezone.now().date() + timedelta(days=10),
        )
        process_book_due(deal)
        book.refresh_from_db()
        assert book.status == SharedBook.Status.OCCUPIED

    def test_non_meeted_no_change(self):
        book = SharedBookFactory(status="O", transferability="RETURN")
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="D",
            due_date=timezone.now().date() - timedelta(days=1),
        )
        process_book_due(deal)
        book.refresh_from_db()
        assert book.status == SharedBook.Status.OCCUPIED

    def test_no_due_date_no_change(self):
        book = SharedBookFactory(status="O", transferability="RETURN")
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="M",
            due_date=None,
        )
        process_book_due(deal)
        book.refresh_from_db()
        assert book.status == SharedBook.Status.OCCUPIED

    def test_notification_sent(self):
        owner = UserFactory()
        keeper = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            keeper=keeper,
            status="O",
            transferability="RETURN",
        )
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="M",
            due_date=timezone.now().date() - timedelta(days=1),
        )
        process_book_due(deal)
        assert (
            Notification.objects.filter(
                notification_type="BOOK_OVERDUE",
            ).count()
            == 2
        )  # keeper + owner

    # ============================================================
    # BR-4.2: 逾期次數遞增
    # ============================================================
    def test_overdue_count_increments_for_return_book(self):
        """BR-4.2: 閱畢即還書籍到期 → 遞增持有者逾期次數"""
        from accounts.models import UserProfile

        owner = UserFactory()
        keeper = UserFactory()
        # 確保 keeper 有 profile
        UserProfile.objects.get_or_create(user=keeper)

        book = SharedBookFactory(
            owner=owner,
            keeper=keeper,
            status="O",
            transferability="RETURN",
        )
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="M",
            due_date=timezone.now().date() - timedelta(days=1),
        )

        # 初始逾期次數
        initial_count = keeper.profile.overdue_count

        process_book_due(deal)

        # 驗證逾期次數 +1
        keeper.profile.refresh_from_db()
        assert keeper.profile.overdue_count == initial_count + 1

    def test_overdue_count_no_increment_for_transfer_book(self):
        """BR-4.2: 開放傳遞書籍到期 → 不遞增逾期次數"""
        from accounts.models import UserProfile

        owner = UserFactory()
        keeper = UserFactory()
        UserProfile.objects.get_or_create(user=keeper)

        book = SharedBookFactory(
            owner=owner,
            keeper=keeper,
            status="O",
            transferability="TRANSFER",
        )
        deal = DealFactory(
            shared_book=book,
            deal_type="TF",
            status="M",
            due_date=timezone.now().date() - timedelta(days=1),
        )

        initial_count = keeper.profile.overdue_count

        process_book_due(deal)

        # 驗證逾期次數不變
        keeper.profile.refresh_from_db()
        assert keeper.profile.overdue_count == initial_count

    def test_overdue_count_no_increment_when_not_due(self):
        """BR-4.2: 未到期 → 不遞增逾期次數"""
        from accounts.models import UserProfile

        owner = UserFactory()
        keeper = UserFactory()
        UserProfile.objects.get_or_create(user=keeper)

        book = SharedBookFactory(
            owner=owner,
            keeper=keeper,
            status="O",
            transferability="RETURN",
        )
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="M",
            due_date=timezone.now().date() + timedelta(days=10),  # 未到期
        )

        initial_count = keeper.profile.overdue_count

        process_book_due(deal)

        keeper.profile.refresh_from_db()
        assert keeper.profile.overdue_count == initial_count
