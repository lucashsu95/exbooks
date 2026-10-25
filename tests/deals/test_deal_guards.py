"""
C3 搬移後的 service 層守衛測試（不經 HTTP），
外加兩個 view 層錯誤轉譯回歸測試。

涵蓋：
- create_exception（EX 持有者身份守衛）
- resolve_exception_deal（例外處置入口）
- send_deal_message / upload_deal_photos（原 view 內守衛）
- confirm_return 互評規則（原 view 內雙重檢查）
- accept() 的 sibling 取消改走 auto_cancel() 轉換
  （與休眠炸彈 cancel() 無關，見 ADR F-1）
- exception_resolve / message_send view 的錯誤訊息轉譯
  （ValidationError 不可用 str()，會秀出方括號）
"""

import io

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from books.models import SharedBook
from deals.models import Deal, DealMessage
from deals.services import deal_service
from tests.factories import DealFactory, SharedBookFactory, UserFactory

pytestmark = pytest.mark.django_db


def _jpeg(name="photo.jpg", color=(30, 120, 200)):
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


class TestCreateException:
    """create_exception：只有持有者（keeper）可申請，書籍狀態轉 E。"""

    def test_keeper_can_apply(self):
        owner = UserFactory()
        keeper = UserFactory()
        book = SharedBookFactory(
            owner=owner, keeper=keeper, status=SharedBook.Status.OCCUPIED
        )
        deal = deal_service.create_exception(book, keeper, description="水漬損傷")
        assert deal.deal_type == Deal.DealType.EXCEPT
        assert deal.applicant == keeper
        assert deal.responder == owner  # EX → Owner 審核
        book.refresh_from_db()
        assert book.status == SharedBook.Status.EXCEPTION
        assert DealMessage.objects.filter(deal=deal, content="水漬損傷").exists()

    def test_non_keeper_rejected(self):
        owner = UserFactory()
        keeper = UserFactory()
        book = SharedBookFactory(
            owner=owner, keeper=keeper, status=SharedBook.Status.OCCUPIED
        )
        with pytest.raises(PermissionDenied, match="只有持有者"):
            deal_service.create_exception(book, owner, description="...")
        assert Deal.objects.filter(deal_type=Deal.DealType.EXCEPT).count() == 0
        book.refresh_from_db()
        assert book.status == SharedBook.Status.OCCUPIED


class TestResolveExceptionDeal:
    def _ex_deal(self, book_status=SharedBook.Status.EXCEPTION, deal_status=Deal.Status.MEETED):
        user = UserFactory()
        book = SharedBookFactory(owner=user, status=book_status)
        deal = DealFactory(
            shared_book=book, deal_type=Deal.DealType.EXCEPT, status=deal_status
        )
        return user, book, deal

    def test_resolve_found(self):
        user, book, deal = self._ex_deal()
        deal_service.resolve_exception_deal(deal, "found")
        deal.refresh_from_db()
        book.refresh_from_db()
        assert deal.status == Deal.Status.DONE
        assert book.status != SharedBook.Status.EXCEPTION

    def test_non_except_deal_rejected(self):
        user, book, deal = self._ex_deal()
        deal.deal_type = Deal.DealType.LOAN
        deal.save(update_fields=["deal_type"])
        with pytest.raises(ValidationError):
            deal_service.resolve_exception_deal(deal, "found")

    def test_book_not_in_exception_rejected(self):
        user, book, deal = self._ex_deal(book_status=SharedBook.Status.TRANSFERABLE)
        with pytest.raises(ValidationError):
            deal_service.resolve_exception_deal(deal, "found")


class TestSendDealMessage:
    def test_finished_deals_rejected(self):
        done = DealFactory(status=Deal.Status.DONE)
        with pytest.raises(ValidationError):
            deal_service.send_deal_message(done, done.applicant, "hi")

        cancelled = DealFactory(status=Deal.Status.CANCELLED)
        with pytest.raises(ValidationError):
            deal_service.send_deal_message(cancelled, cancelled.applicant, "hi")

    def test_active_deal_creates_message(self):
        deal = DealFactory()  # REQUESTED
        deal_service.send_deal_message(deal, deal.applicant, "你好")
        assert DealMessage.objects.filter(deal=deal, content="你好").exists()


class TestUploadDealPhotos:
    def _transfer_book(self, deal):
        deal.shared_book.transferability = SharedBook.Transferability.TRANSFER
        deal.shared_book.save()

    def test_non_meeted_rejected(self):
        deal = DealFactory(status=Deal.Status.REQUESTED)
        self._transfer_book(deal)
        with pytest.raises(ValidationError):
            deal_service.upload_deal_photos(deal, deal.shared_book.keeper, [_jpeg()])

    def test_return_book_rejected(self):
        deal = DealFactory(status=Deal.Status.MEETED)  # factory 預設 RETURN
        assert deal.shared_book.transferability == SharedBook.Transferability.RETURN
        with pytest.raises(ValidationError):
            deal_service.upload_deal_photos(deal, deal.shared_book.keeper, [_jpeg()])

    def test_meeted_transfer_book_uploads(self):
        deal = DealFactory(status=Deal.Status.MEETED)
        self._transfer_book(deal)
        created = deal_service.upload_deal_photos(
            deal, deal.shared_book.keeper, [_jpeg()], caption="ok"
        )
        assert len(created) == 1
        assert created[0].caption == "ok"


class TestConfirmReturnRatingRule:
    def test_unrated_non_force_rejected(self):
        deal = DealFactory(status=Deal.Status.MEETED)
        with pytest.raises(ValidationError, match="互評"):
            deal_service.confirm_return(deal, confirmed_by=deal.responder, force=False)


class TestAcceptCancelsSiblingsViaTransition:
    def test_sibling_request_auto_cancelled(self):
        """BR-15：接受後同一本書的其他 REQUESTED 申請取消（經 auto_cancel() 轉換）。"""
        user_a = UserFactory()
        user_b = UserFactory()
        book = SharedBookFactory(owner=user_b, status=SharedBook.Status.TRANSFERABLE)
        deal_a = DealFactory(shared_book=book, applicant=user_a)
        deal_b = DealFactory(shared_book=book, applicant=UserFactory())

        assert deal_b.status == Deal.Status.REQUESTED
        deal_service.accept_deal(deal_a)

        deal_b.refresh_from_db()
        deal_a.refresh_from_db()
        assert deal_a.status == Deal.Status.RESPONDED
        assert deal_b.status == Deal.Status.CANCELLED
        # 書被預約（V），不被 sibling 取消時的還書副作用蓋掉
        book.refresh_from_db()
        assert book.status == SharedBook.Status.RESERVED


class TestExceptionResolveView:
    """exception_resolve view 成功路徑回歸測試。

    背景：重構時刪了 `resolution = form.cleaned_data[...]`，成功訊息卻仍引用
    未定義的 `resolution`——成功處置必拋 NameError、被 except Exception 吃掉，
    使用者看到英文機器訊息而非成功重導向。
    """

    def test_post_success_as_owner(self, client):
        owner = UserFactory()
        keeper = UserFactory()
        book = SharedBookFactory(
            owner=owner, keeper=keeper, status=SharedBook.Status.EXCEPTION
        )
        deal = DealFactory(
            shared_book=book, deal_type=Deal.DealType.EXCEPT, status=Deal.Status.MEETED
        )

        client.force_login(owner)
        url = reverse("deals:exception_resolve", kwargs={"pk": deal.pk})
        response = client.post(url, {"resolution": "found"})

        assert response.status_code == 302
        assert response.url == reverse("books:detail", kwargs={"pk": book.pk})
        deal.refresh_from_db()
        book.refresh_from_db()
        assert deal.status == Deal.Status.DONE
        assert book.status != SharedBook.Status.EXCEPTION

    def test_post_error_message_translated(self, client):
        """ValidationError 轉譯為純中文；str(e) 的方括號/引號不得秀給使用者。"""
        owner = UserFactory()
        keeper = UserFactory()
        book = SharedBookFactory(
            owner=owner, keeper=keeper, status=SharedBook.Status.TRANSFERABLE
        )
        deal = DealFactory(
            shared_book=book, deal_type=Deal.DealType.EXCEPT, status=Deal.Status.MEETED
        )

        client.force_login(owner)
        url = reverse("deals:exception_resolve", kwargs={"pk": deal.pk})
        response = client.post(url, {"resolution": "found"})

        assert response.status_code == 200  # 失敗回渲染表單
        messages_shown = [str(m) for m in response.context["messages"]]
        assert "書籍不在例外狀態" in messages_shown
        assert not any("[" in m for m in messages_shown)


class TestDealMessageSendView:
    """message_send（HTMX endpoint）400 body 必須是純中文，不是 str(ValidationError)。"""

    def test_send_to_finished_deal_returns_plain_400(self, client):
        deal = DealFactory(status=Deal.Status.DONE)
        client.force_login(deal.applicant)
        response = client.post(
            reverse("deals:message_send", kwargs={"pk": deal.pk}),
            {"content": "hi"},
        )
        assert response.status_code == 400
        body = response.content.decode("utf-8")
        assert "此交易已結束，無法再發送留言。" in body
        assert "[" not in body
