"""Tests for books app forms."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict
from PIL import Image

from books.forms import BookAddForm
from books.models import OfficialBook, SharedBook


@pytest.fixture
def sample_image():
    """建立測試用的圖片檔案"""
    img = Image.new("RGB", (100, 100), color="red")
    img_io = BytesIO()
    img.save(img_io, format="JPEG")
    img_io.seek(0)
    return SimpleUploadedFile("test.jpg", img_io.read(), content_type="image/jpeg")


@pytest.fixture
def valid_book_data():
    """有效的書籍表單資料"""
    return {
        "isbn": "9789571234567",
        "title": "測試書籍",
        "author": "測試作者",
        "publisher": "測試出版社",
        "category": OfficialBook.Category.OTHER,
        "transferability": SharedBook.Transferability.RETURN,
        "condition_description": "九成新",
        "loan_duration_days": 30,
    }


@pytest.mark.django_db
class TestBookAddForm:
    """BookAddForm 測試"""

    def test_form_without_photos_is_invalid(self, valid_book_data):
        """測試：沒有上傳照片時表單應該無效"""
        files = MultiValueDict()
        form = BookAddForm(data=valid_book_data, files=files)
        assert not form.is_valid()
        assert "請至少上傳一張書況照片" in str(form.errors)

    def test_form_with_one_photo_is_valid(self, valid_book_data, sample_image):
        """測試：上傳一張照片時表單應該有效"""
        files = MultiValueDict({"photos": [sample_image]})
        form = BookAddForm(data=valid_book_data, files=files)
        assert form.is_valid(), f"表單錯誤: {form.errors}"

    def test_form_with_multiple_photos_is_valid(self, valid_book_data, sample_image):
        """測試：上傳多張照片時表單應該有效"""
        # 建立第二張圖片
        img2 = Image.new("RGB", (100, 100), color="blue")
        img2_io = BytesIO()
        img2.save(img2_io, format="JPEG")
        img2_io.seek(0)
        sample_image2 = SimpleUploadedFile(
            "test2.jpg", img2_io.read(), content_type="image/jpeg"
        )

        files = MultiValueDict({"photos": [sample_image, sample_image2]})
        form = BookAddForm(data=valid_book_data, files=files)
        assert form.is_valid(), f"表單錯誤: {form.errors}"

    def test_form_with_empty_photos_list_is_invalid(self, valid_book_data):
        """測試：photos 為空列表時表單應該無效"""
        files = MultiValueDict({"photos": []})
        form = BookAddForm(data=valid_book_data, files=files)
        assert not form.is_valid()
        assert "請至少上傳一張書況照片" in str(form.errors)
