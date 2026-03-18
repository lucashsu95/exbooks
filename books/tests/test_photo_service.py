import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from books.services.photo_service import validate_and_process


def create_test_image(format="JPEG", size=(100, 100), color="red", mode="RGB"):
    file = io.BytesIO()
    image = Image.new(mode, size, color)
    image.save(file, format)
    file.seek(0)
    return file


class TestPhotoService:
    def test_validate_and_process_valid_jpg(self):
        img_data = create_test_image("JPEG")
        uploaded_file = SimpleUploadedFile(
            "test.jpg", img_data.read(), content_type="image/jpeg"
        )

        processed_file = validate_and_process(uploaded_file)

        assert processed_file.name.endswith(".jpg")
        # 驗證是否為有效的圖片
        img = Image.open(processed_file)
        assert img.format == "JPEG"
        assert img.mode == "RGB"

    def test_validate_and_process_valid_png(self):
        img_data = create_test_image("PNG")
        uploaded_file = SimpleUploadedFile(
            "test.png", img_data.read(), content_type="image/png"
        )

        processed_file = validate_and_process(uploaded_file)

        assert processed_file.name.endswith(".jpg")  # 統一轉換為 jpg
        img = Image.open(processed_file)
        assert img.format == "JPEG"

    def test_rgba_to_rgb_conversion(self):
        # 建立一個帶有透明度的 PNG
        file = io.BytesIO()
        image = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        image.save(file, "PNG")
        file.seek(0)
        uploaded_file = SimpleUploadedFile(
            "transparent.png", file.read(), content_type="image/png"
        )

        processed_file = validate_and_process(uploaded_file)
        img = Image.open(processed_file)
        assert img.mode == "RGB"

    def test_invalid_extension(self):
        uploaded_file = SimpleUploadedFile(
            "test.txt", b"not an image", content_type="text/plain"
        )
        with pytest.raises(ValidationError, match="不支援的檔案格式"):
            validate_and_process(uploaded_file)

    def test_invalid_mime_type(self):
        img_data = create_test_image("JPEG")
        uploaded_file = SimpleUploadedFile(
            "test.jpg", img_data.read(), content_type="application/pdf"
        )
        with pytest.raises(ValidationError, match="不支援的 MIME 類型"):
            validate_and_process(uploaded_file)

    def test_compression_large_file(self):
        # 建立一個大尺寸圖片
        img_data = create_test_image("JPEG", size=(2000, 2000))
        uploaded_file = SimpleUploadedFile(
            "large.jpg", img_data.read(), content_type="image/jpeg"
        )

        processed_file = validate_and_process(uploaded_file)
        # 確保處理後的檔案大小在限制內 (5MB)
        assert processed_file.size <= 5 * 1024 * 1024

    def test_corrupted_image(self):
        uploaded_file = SimpleUploadedFile(
            "corrupted.jpg", b"not a real image content", content_type="image/jpeg"
        )
        with pytest.raises(ValidationError, match="無法開啟圖片檔案"):
            validate_and_process(uploaded_file)

    def test_exif_rotation_handling(self):
        # 建立一個帶有 EXIF 旋轉資訊 (Orientation 6: 順時針 90 度) 的圖片
        # 原始尺寸 100x50
        img = Image.new("RGB", (100, 50), "red")
        exif = img.getexif()
        exif[274] = 6  # Orientation tag

        file = io.BytesIO()
        img.save(file, "JPEG", exif=exif)
        file.seek(0)

        uploaded_file = SimpleUploadedFile(
            "rotate.jpg", file.read(), content_type="image/jpeg"
        )
        processed_file = validate_and_process(uploaded_file)

        processed_img = Image.open(processed_file)
        # 處理後尺寸應變為 50x100
        assert processed_img.size == (50, 100)
