import io
import os

from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile
from PIL import Image, ImageOps

MAX_SIZE_MB = 5
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}


def validate_and_process(image_file):
    """
    驗證並處理書況照片。
    1. 驗證格式 (JPG/PNG)
    2. 驗證大小 (最大 5MB)
    3. 處理 EXIF 旋轉
    4. 自動壓縮 (若超過限制或為了節省空間)
    5. 返回處理後的 ImageFile
    """
    # 1. 驗證副檔名
    ext = os.path.splitext(image_file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"不支援的檔案格式：{ext}。僅支援 JPG 和 PNG。")

    # 2. 驗證 MIME type
    if image_file.content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(f"不支援的 MIME 類型：{image_file.content_type}。")

    # 3. 讀取圖片
    try:
        img = Image.open(image_file)
    except Exception as e:
        raise ValidationError(f"無法開啟圖片檔案：{str(e)}")

    # 4. 處理 EXIF 旋轉
    img = ImageOps.exif_transpose(img)

    # 5. 統一轉換為 RGB (處理 RGBA 或 P 模式，並準備轉存為 JPEG)
    if img.mode in ("RGBA", "P"):
        # 建立白色背景以處理透明度
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 6. 壓縮處理
    output = io.BytesIO()
    quality = 85

    # 初始儲存為 JPEG
    img.save(output, format="JPEG", quality=quality, optimize=True)

    # 如果仍然超過 5MB，降低品質
    while output.tell() > MAX_SIZE_BYTES and quality > 30:
        quality -= 10
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)

    # 如果品質降到 30 還是太大，縮小尺寸
    if output.tell() > MAX_SIZE_BYTES:
        while output.tell() > MAX_SIZE_BYTES:
            width, height = img.size
            if width <= 100 or height <= 100:
                break
            img = img.resize(
                (int(width * 0.8), int(height * 0.8)), Image.Resampling.LANCZOS
            )
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)

    # 最終檢查，如果還是太大 (極端情況)，拋出錯誤
    if output.tell() > MAX_SIZE_BYTES:
        raise ValidationError("圖片檔案太大，即使壓縮後仍超過 5MB 限制。")

    output.seek(0)

    # 建立新的 ImageFile，統一使用 .jpg 副檔名
    new_filename = os.path.splitext(image_file.name)[0] + ".jpg"
    return ImageFile(output, name=new_filename)
