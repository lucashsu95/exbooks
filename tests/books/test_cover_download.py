"""
封面 URL 下載的回歸測試（H-3，ADR F-8）。

- SSRF：只允許 http/https、解析後的 IP 必須是公網位址、不跟隨重導向、
  實際連線釘選到已驗證的 IP（避免 DNS rebinding）。
- 儲存型 XSS：下載內容必須是圖片，一律重新編碼並以 .jpg 儲存。
"""

import io
import socket

import httpx
import pytest
from django.core.exceptions import ValidationError
from PIL import Image

from books.models import SharedBook
from books.services import cover_service, publish_book
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PUBLIC_IP = "93.184.216.34"


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGBA", (30, 40), (10, 200, 10, 128)).save(buf, format="PNG")
    return buf.getvalue()


def _fake_dns(ip):
    def getaddrinfo(host, port, *args, **kwargs):
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (ip, port))]

    return getaddrinfo


@pytest.fixture
def serve(monkeypatch):
    """讓 download_cover 連到 MockTransport；回傳記錄 request 的 list。"""
    seen = []

    def install(handler, ip=PUBLIC_IP):
        def _handler(request):
            seen.append(request)
            return handler(request)

        monkeypatch.setattr(cover_service.socket, "getaddrinfo", _fake_dns(ip))
        monkeypatch.setattr(
            cover_service,
            "_make_client",
            lambda: httpx.Client(transport=httpx.MockTransport(_handler)),
        )
        return seen

    return install


class TestDownloadCoverSSRF:
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://example.com/a.jpg",
            "gopher://example.com/",
            "http:///nohost.jpg",
            "http://user:pw@example.com/a.jpg",
        ],
    )
    def test_rejects_bad_scheme_or_url(self, url, serve):
        seen = serve(lambda r: httpx.Response(200, content=_png_bytes()))
        with pytest.raises(ValidationError):
            cover_service.download_cover(url)
        assert seen == []

    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",
            "10.0.0.5",
            "172.16.3.4",
            "192.168.1.1",
            "169.254.169.254",
            "0.0.0.0",
            "100.64.0.1",
            "::1",
            "fd00::1",
            "fe80::1",
            # 審查後修正：IPv6 轉譯／隧道前綴可內嵌任意 IPv4（含內網）
            "64:ff9b::7f00:1",  # NAT64 well-known → 127.0.0.1
            "64:ff9b::5db8:d822",  # NAT64 well-known（嵌公網 IP 也拒）
            "64:ff9b:1::a00:5",  # NAT64 local-use
            "2002:7f00:1::1",  # 6to4 → 127.0.0.1
            "2002:5db8:d822::1",  # 6to4（嵌公網 IP 也拒）
            "2001:0:4136:e378:8000:63bf:3fff:fdd2",  # Teredo
        ],
    )
    def test_rejects_non_public_ip(self, ip, serve):
        seen = serve(lambda r: httpx.Response(200, content=_png_bytes()), ip=ip)
        with pytest.raises(ValidationError):
            cover_service.download_cover("http://cover.test/a.jpg")
        assert seen == []

    @pytest.mark.parametrize(
        "url",
        [
            "http://cover.test:8080/a.jpg",
            "https://cover.test:8443/a.jpg",
            "http://cover.test:443/a.jpg",
            "https://cover.test:80/a.jpg",
            "http://cover.test:6379/a.jpg",
        ],
    )
    def test_rejects_non_default_port(self, url, serve):
        seen = serve(lambda r: httpx.Response(200, content=_png_bytes()))
        with pytest.raises(ValidationError):
            cover_service.download_cover(url)
        assert seen == []

    @pytest.mark.parametrize(
        "url", ["http://cover.test:80/a.png", "https://cover.test:443/a.png"]
    )
    def test_allows_explicit_default_port(self, url, serve):
        seen = serve(lambda r: httpx.Response(200, content=_png_bytes()))
        assert cover_service.download_cover(url) == _png_bytes()
        assert seen[0].headers["Host"] == "cover.test"

    def test_does_not_follow_redirects(self, serve):
        seen = serve(
            lambda r: httpx.Response(
                302, headers={"Location": "http://169.254.169.254/latest/meta-data"}
            )
        )
        with pytest.raises(ValidationError):
            cover_service.download_cover("http://cover.test/a.jpg")
        assert len(seen) == 1

    def test_rejects_oversized_body(self, serve):
        big = b"\0" * (cover_service.MAX_COVER_BYTES + 1)
        serve(lambda r: httpx.Response(200, content=big))
        with pytest.raises(ValidationError):
            cover_service.download_cover("http://cover.test/a.jpg")

    def test_connects_to_pinned_ip_with_original_host(self, serve):
        seen = serve(lambda r: httpx.Response(200, content=_png_bytes()))
        data = cover_service.download_cover("https://cover.test/img/a.png?x=1")
        assert data == _png_bytes()
        (req,) = seen
        assert req.url.host == PUBLIC_IP
        assert req.url.path == "/img/a.png"
        assert req.url.query == b"x=1"
        assert req.headers["Host"] == "cover.test"
        assert req.extensions.get("sni_hostname") == "cover.test"


def _publish_data():
    return {
        "isbn": "9787770009991",
        "title": "封面測試",
        "author": "作者",
        "publisher": "出版社",
        "category": "TECH",
        "transferability": SharedBook.Transferability.RETURN,
        "condition_description": "九成新",
        "loan_duration_days": 21,
    }


class TestCoverFormatsMatchPhotoService:
    """審查後修正：封面允許格式與 photo_service 實際接受的一致（JPG / PNG）。"""

    def test_single_source_of_allowed_formats(self):
        from books.services import photo_service

        assert cover_service.ALLOWED_IMAGE_FORMATS is photo_service.ALLOWED_IMAGE_FORMATS
        assert set(photo_service.ALLOWED_IMAGE_FORMATS) == {"JPEG", "PNG"}

    @pytest.mark.parametrize("fmt", ["GIF", "WEBP"])
    def test_rejects_formats_photo_service_does_not_accept(self, fmt):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), (1, 2, 3)).save(buf, format=fmt)
        with pytest.raises(ValidationError):
            cover_service.process_cover_bytes(buf.getvalue(), "x.jpg")

    def test_photo_service_rejects_gif_disguised_as_png(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from books.services.photo_service import validate_and_process

        buf = io.BytesIO()
        Image.new("RGB", (10, 10), (1, 2, 3)).save(buf, format="GIF")
        upload = SimpleUploadedFile("x.png", buf.getvalue(), content_type="image/png")
        with pytest.raises(ValidationError):
            validate_and_process(upload)

    def test_fetch_cover_image_names_file_by_basename(self, serve):
        serve(lambda r: httpx.Response(200, content=_png_bytes()))
        cover = cover_service.fetch_cover_image("http://cover.test/a.png", "abc")
        assert cover.name == cover_service.cover_filename("abc") == "abc.jpg"


def _jpeg_upload():
    from django.core.files.uploadedfile import SimpleUploadedFile

    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (1, 2, 3)).save(buf, format="JPEG")
    return SimpleUploadedFile("p.jpg", buf.getvalue(), content_type="image/jpeg")


class TestPublishWithCoverUrl:
    def test_html_payload_is_not_stored(self, serve):
        serve(
            lambda r: httpx.Response(
                200,
                content=b"<html><script>alert(1)</script></html>",
                headers={"Content-Type": "text/html"},
            )
        )
        shared = publish_book(
            UserFactory(), _publish_data(), photos=[_jpeg_upload()], cover_url="http://cover.test/evil.html"
        )
        assert shared.status == SharedBook.Status.TRANSFERABLE
        assert not shared.official_book.cover_image

    def test_image_is_reencoded_as_jpg(self, serve):
        serve(lambda r: httpx.Response(200, content=_png_bytes()))
        shared = publish_book(
            UserFactory(), _publish_data(), photos=[_jpeg_upload()], cover_url="http://cover.test/cover.html"
        )
        cover = shared.official_book.cover_image
        assert cover
        assert cover.name.endswith(".jpg")
        cover.open("rb")
        with Image.open(cover) as img:
            assert img.format == "JPEG"

    def test_private_target_is_not_fetched(self, serve):
        seen = serve(lambda r: httpx.Response(200, content=_png_bytes()), ip="127.0.0.1")
        shared = publish_book(
            UserFactory(), _publish_data(), photos=[_jpeg_upload()], cover_url="http://localhost:8000/admin/"
        )
        assert seen == []
        assert not shared.official_book.cover_image
