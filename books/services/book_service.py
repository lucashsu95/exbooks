"""
書籍領域服務。

此模組封裝 SharedBook 的發布（publish）、編輯與狀態轉換邏輯，
使用 django-fsm 管理狀態。
Service 層負責：
- 權限檢查
- 跨 Model 事務協調
- 觸發 FSM 狀態轉換

副作用（通知）由 Signal 處理。
錯誤契約：失敗一律 raise ValidationError / PermissionDenied（訊息為
使用者可讀的中文）；View 層負責轉譯為 messages 與 HTTP 回應。
"""

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files import File
from django.core.files.storage import Storage
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from django_fsm import can_proceed

from books.models import BookPhoto, OfficialBook, SharedBook, WishListItem
from books.services import cover_service
from books.services.photo_service import validate_and_process as process_book_photo
from deals.services.notification_service import notify_book_available

logger = logging.getLogger(__name__)

# ============================================================================
# 書籍上架/下架
# ============================================================================


def list_book(shared_book):
    """
    將書籍狀態從 S（暫不開放）切換為 T（可移轉），開放借閱。

    使用 FSM 狀態轉換：SUSPENDED → TRANSFERABLE

    副作用（由 Signal 處理）：
    - 記錄上架時間
    - 通知願望清單中的使用者

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(shared_book.list_for_transfer):
        raise ValidationError(
            f"只有「暫不開放」的書籍可以開放，目前狀態為「{shared_book.get_status_display()}」"
        )

    shared_book.list_for_transfer()
    # 記錄上架時間（在 save 之前設定）
    shared_book.listed_at = timezone.now()
    shared_book.save()

    # 通知願望書車中的使用者此書已可借閱
    wish_items = WishListItem.objects.filter(
        official_book=shared_book.official_book,
    ).select_related("user")
    for item in wish_items:
        notify_book_available(item.user, shared_book)

    logger.info(
        "book listed",
        extra={
            "book_id": shared_book.id,
            "owner_id": shared_book.owner_id,
            "wish_notified": wish_items.count(),
        },
    )


def suspend_book(shared_book):
    """
    將書籍狀態從 T（可移轉）切換為 S（暫不開放），暫停接受借閱。

    使用 FSM 狀態轉換：TRANSFERABLE → SUSPENDED

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(shared_book.suspend):
        raise ValidationError(
            f"只有「可移轉」的書籍可以暫停，目前狀態為「{shared_book.get_status_display()}」"
        )

    shared_book.suspend()
    shared_book.save()

    logger.info("book suspended", extra={"book_id": shared_book.id})


# ============================================================================
# 發布（publish）/ 編輯 / 狀態切換
# ============================================================================


# 使用者可「補空白」的共用書目欄位，以及各欄位視同空白的值
# （分類的預設值「其他（未分類）」視同空白）。
_CATALOG_BLANK_VALUES: dict[str, frozenset[str]] = {
    "title": frozenset({""}),
    "author": frozenset({""}),
    "publisher": frozenset({""}),
    "category": frozenset({"", OfficialBook.Category.OTHER}),
}
CATALOG_FILLABLE_FIELDS = tuple(_CATALOG_BLANK_VALUES)


def _clean_catalog_value(value: object) -> str:
    return str(value or "").strip()


def _is_blank_catalog_value(field: str, value: object) -> bool:
    return _clean_catalog_value(value) in _CATALOG_BLANK_VALUES[field]


def _lock_official_book(official_book: OfficialBook) -> OfficialBook:
    """重新從資料庫取出並鎖住該 OfficialBook 列（需在 transaction 內呼叫）。"""
    return OfficialBook.objects.select_for_update().get(pk=official_book.pk)


def fill_blank_catalog_fields(
    official_book: OfficialBook, data: Mapping[str, Any]
) -> list[str]:
    """
    共用書目保護：既有 OfficialBook 只補空白欄位，不覆寫已有內容。

    OfficialBook 由多位 owner 的 SharedBook 共用，一般使用者發布同 ISBN
    或編輯自己的書時不能改掉別人看到的書目；更正既有內容由管理員在
    Django admin 處理。

    併發安全：以 select_for_update 鎖住並重新讀取該列後才判斷哪些欄位
    仍是空白，呼叫端手上的 instance 即使過時也不會覆寫別人剛補上的值；
    結束後把最新的書目欄位同步回 official_book。

    Returns:
        實際被補上的欄位名稱
    """
    with transaction.atomic():
        locked = _lock_official_book(official_book)
        filled = []
        for field in CATALOG_FILLABLE_FIELDS:
            incoming = _clean_catalog_value(data.get(field))
            if _is_blank_catalog_value(field, incoming):
                continue
            if _is_blank_catalog_value(field, getattr(locked, field)):
                setattr(locked, field, incoming)
                filled.append(field)
        if filled:
            locked.save(update_fields=[*filled, "updated_at"])

    for field in CATALOG_FILLABLE_FIELDS:
        setattr(official_book, field, getattr(locked, field))
    return filled


# 本次發布已寫入 storage 的檔案（storage, name），事務回滾時據以刪除
SavedFiles = list[tuple[Storage, str]]


@contextmanager
def _delete_saved_files_on_error() -> Iterator[SavedFiles]:
    """
    區塊內拋例外（事務已回滾）時，刪除區塊中已寫入 storage 的檔案，避免孤兒檔。

    Django 沒有 on_rollback 掛勾；呼叫端把 transaction.atomic() 放在此區塊內，
    例外穿出 atomic（回滾完成）後在這裡清檔，再原樣拋出。
    """
    saved: SavedFiles = []
    try:
        yield saved
    except BaseException:
        for storage, name in saved:
            try:
                storage.delete(name)
            except Exception:
                logger.exception("orphan cover cleanup failed", extra={"file": name})
        raise


def _save_cover(
    instance: OfficialBook | SharedBook,
    content: File,
    saved_files: SavedFiles | None,
) -> None:
    """把已處理的封面寫入 instance.cover_image 並只更新該欄位。"""
    field_file = instance.cover_image
    field_file.save(content.name, content, save=False)
    if saved_files is not None:
        saved_files.append((field_file.storage, field_file.name))
    instance.save(update_fields=["cover_image", "updated_at"])


def _attach_cover(
    official_book: OfficialBook,
    shared_book: SharedBook,
    uploaded_cover: UploadedFile | None = None,
    cover_url: str = "",
    saved_files: SavedFiles | None = None,
) -> None:
    """
    附上封面（需在 transaction 內呼叫）。

    共用書目沒有封面時視同空白欄位：上傳檔（優先）或下載 cover_url 補到
    OfficialBook。共用書目已有封面時，上傳檔只存到這一冊的 SharedBook，
    不取代其他人看到的共用封面；cover_url 則略過。

    上傳檔一律走書況照片的驗證／重新編碼流程（JPG/PNG、5MB、輸出 .jpg），
    不合法時 raise ValidationError。是否「仍為空白」在鎖住 OfficialBook 後
    重新判斷，併發發布不會互相覆寫封面。下載失敗只記錄日誌、不中斷發布。
    寫入的檔案記錄到 saved_files，供事務回滾時清除。
    """
    if uploaded_cover:
        processed = process_book_photo(uploaded_cover)
        locked = _lock_official_book(official_book)
        if locked.cover_image:
            _save_cover(shared_book, processed, saved_files)
        else:
            _save_cover(locked, processed, saved_files)
            official_book.cover_image = locked.cover_image.name
        return

    if not cover_url or official_book.cover_image:
        return

    try:
        # SSRF 防護 + 圖片驗證與重新編碼（一律 .jpg），見 cover_service
        cover_file = cover_service.fetch_cover_image(cover_url, official_book.pk)
    except Exception:
        logger.exception(
            "cover download failed",
            extra={
                "official_book_id": official_book.pk,
                "isbn": official_book.isbn,
                "cover_url": cover_url,
            },
        )
        return

    locked = _lock_official_book(official_book)
    if locked.cover_image:
        # 下載期間已有人補上共用封面：捨棄下載結果，不覆寫
        official_book.cover_image = locked.cover_image.name
        return
    _save_cover(locked, cover_file, saved_files)
    official_book.cover_image = locked.cover_image.name


def _create_book_photo(shared_book, uploader, image):
    processed = process_book_photo(image)
    BookPhoto.objects.create(
        shared_book=shared_book,
        uploader=uploader,
        photo=processed,
    )


def publish_book(owner, data, photos=(), cover=None, cover_url=""):
    """
    發布（publish）：將一冊實體書上架為 SharedBook 並進入 TRANSFERABLE 狀態。

    完整流程：
    1. OfficialBook 依 ISBN 建立；已存在時只補空白欄位、不覆寫
       （見 fill_blank_catalog_fields）
    2. 建立 SharedBook（owner = keeper = 發布者，初始狀態 SUSPENDED）
    3. 附封面（見 _attach_cover：共用書目無封面才補上；已有封面時
       上傳檔只存在這一冊；下載失敗不中斷）
    4. 寫入書況照片
    5. 透過 list_book() 走合法 FSM 通道 S → T
       （副作用：記錄上架時間、通知願望清單使用者）

    步驟 1–4 為單一事務（失敗全回滾）；步驟 5 在事務外執行
    （通知是 Celery 非同步、不可回滾的副作用）。步驟 5 失敗時書留在
    SUSPENDED，發布者可用 toggle_listing 重新開放。

    Args:
        owner: 發布者（同時成為 owner 與 keeper）
        data: form 校驗後的 dict，需含 isbn/title/author/publisher/category
              及 SharedBook 欄位 transferability/condition_description/
              loan_duration_days
        photos: 書況照片（上傳檔）的可迭代集
        cover: 手動上傳的封面圖片（可選）
        cover_url: 封面 URL（無上傳封面時下載；失敗不中斷發布）

    Returns:
        SharedBook: 已進入 TRANSFERABLE 狀態的新書

    Raises:
        ValidationError: 照片驗證/處理失敗
    """
    isbn = data["isbn"]
    with _delete_saved_files_on_error() as saved_files, transaction.atomic():
        off_book, created = OfficialBook.objects.get_or_create(
            isbn=isbn,
            defaults={
                "title": _clean_catalog_value(data["title"]),
                "author": _clean_catalog_value(data.get("author")),
                "publisher": _clean_catalog_value(data.get("publisher")),
                "category": data["category"],
            },
        )
        if not created:
            fill_blank_catalog_fields(off_book, data)

        shared = SharedBook.objects.create(
            official_book=off_book,
            owner=owner,
            keeper=owner,
            transferability=data["transferability"],
            condition_description=data.get("condition_description", ""),
            loan_duration_days=data.get("loan_duration_days", 30),
        )

        _attach_cover(off_book, shared, cover, cover_url, saved_files)

        for image in photos:
            _create_book_photo(shared, owner, image)

    # 透過合法 FSM 通道上架；listed_at 與願望清單通知由 list_book 處理
    list_book(shared)

    logger.info(
        "book published",
        extra={"owner_id": owner.pk, "shared_book_id": shared.pk, "isbn": isbn},
    )
    return shared


# ============================================================================
# Level 0 權限守衛（TrustLevel 編輯/切換規則的單一來源，見 GLOSSARY）
# ============================================================================

BOOK_EDIT_DENIED = (
    "新手等級 (Level 0) 尚無權限編輯書籍資訊，請多參與交易提升等級。"
)
BOOK_TOGGLE_DENIED = "新手等級 (Level 0) 尚無權限切換書籍狀態。"


def assert_book_edit_permission(user):
    """業務規則：Level 0 使用者不能編輯書籍資訊（book_edit / update_book 共用）。"""
    if user.profile.trust_level == 0:
        raise PermissionDenied(BOOK_EDIT_DENIED)


def assert_book_toggle_permission(user):
    """業務規則：Level 0 使用者不能切換書籍狀態（toggle_status / toggle_listing 共用）。"""
    if user.profile.trust_level == 0:
        raise PermissionDenied(BOOK_TOGGLE_DENIED)


def update_book(book, user, data, photos=()):
    """
    更新書籍資訊（SharedBook 欄位 + 新增照片；OfficialBook 只補空白欄位）。

    Args:
        book: 要更新的 SharedBook（ownership 由 View 層以
              get_object_or_404(owner=user) 保證）
        user: 操作者
        data: form 校驗後的 dict，需含 title/author/publisher/category 及
              transferability/min_trust_level/condition_description/
              loan_duration_days
        photos: 新增的書況照片（上傳檔）的可迭代集

    Returns:
        SharedBook: 更新後的書籍

    Raises:
        PermissionDenied: Level 0 使用者
        ValidationError: 照片驗證/處理失敗
    """
    assert_book_edit_permission(user)

    with transaction.atomic():
        # 共用書目只補空白欄位，不覆寫其他 owner 也看得到的內容
        fill_blank_catalog_fields(book.official_book, data)

        book.transferability = data["transferability"]
        book.min_trust_level = data["min_trust_level"]
        book.condition_description = data.get("condition_description", "")
        book.loan_duration_days = data["loan_duration_days"]
        book.save()

        for image in photos:
            _create_book_photo(book, user, image)

    logger.info(
        "book updated",
        extra={"user_id": user.pk, "shared_book_id": book.pk},
    )
    return book


def toggle_listing(book, user):
    """
    切換書籍借閱狀態 S ↔ T。其他狀態（O/E/R…）不可切換。

    Args:
        book: 要切換的 SharedBook（ownership 由 View 層保證）
        user: 操作者

    Returns:
        str: 切換後的狀態值

    Raises:
        PermissionDenied: Level 0 使用者
        ValidationError: 目前狀態不可切換
    """
    assert_book_toggle_permission(user)

    if book.status == SharedBook.Status.SUSPENDED:
        list_book(book)
    elif book.status == SharedBook.Status.TRANSFERABLE:
        suspend_book(book)
    else:
        raise ValidationError("書籍狀態無法切換")

    logger.info(
        "book listing toggled",
        extra={"user_id": user.pk, "shared_book_id": book.pk, "status": book.status},
    )
    return book.status


# ============================================================================
# 套書驗證
# ============================================================================


def validate_book_set_completeness(book_set):
    """
    BR-7: 驗證套書中所有書籍是否都處於可借出狀態。
    套書必須整套借出，若有任一冊不可借出則拒絕。

    Returns:
        list[SharedBook]: 套書中所有書籍

    Raises:
        ValidationError: 若套書中有書籍不可借出
    """
    books = list(book_set.books.select_related("official_book"))

    if not books:
        logger.warning("validate_book_set_completeness: empty set", extra={"book_set_id": book_set.id})
        raise ValidationError("此套書沒有包含任何書籍")

    unavailable = [b for b in books if b.status != SharedBook.Status.TRANSFERABLE]

    if unavailable:
        titles = ", ".join(str(b) for b in unavailable)
        logger.warning(
            "validate_book_set_completeness: books unavailable",
            extra={
                "book_set_id": book_set.id,
                "unavailable_count": len(unavailable),
            },
        )
        raise ValidationError(
            f"套書中以下書籍目前無法借出：{titles}。套書必須整套借出。"
        )

    logger.debug(
        "validate_book_set_completeness: ok",
        extra={"book_set_id": book_set.id, "book_count": len(books)},
    )
    return books


# ============================================================================
# 例外狀況處理
# ============================================================================


def declare_exception(shared_book):
    """
    將書籍狀態切換為 E（例外狀況）。

    使用 FSM 狀態轉換：TRANSFERABLE/OCCUPIED/RESTORABLE → EXCEPTION

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(shared_book.declare_exception):
        raise ValidationError(
            f"書籍目前狀態「{shared_book.get_status_display()}」無法宣告例外"
        )

    shared_book.declare_exception()
    shared_book.save()

    logger.info("exception declared", extra={"book_id": shared_book.id})


def resolve_exception(shared_book, resolution):
    """
    處置例外狀況：遺失、損毀、或尋獲歸還。

    Args:
        shared_book: 書籍實例
        resolution: 'lost' | 'destroyed' | 'found'

    Raises:
        ValidationError: 如果狀態轉換不允許或處置方式無效
    """
    resolution_methods = {
        "lost": shared_book.mark_as_lost,
        "destroyed": shared_book.mark_as_destroyed,
        "found": shared_book.mark_as_found,
    }

    if resolution not in resolution_methods:
        raise ValidationError(f"無效的處置方式：{resolution}")

    method = resolution_methods[resolution]
    if not can_proceed(method):
        raise ValidationError("只有「例外狀況」的書籍可以處置")

    method()
    shared_book.save()

    logger.info(
        "exception resolved",
        extra={"book_id": shared_book.id, "resolution": resolution},
    )
