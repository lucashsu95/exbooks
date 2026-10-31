"""
封面 URL 下載服務（ADR F-8）。

cover_url 來自使用者輸入，下載時必須防範：
- SSRF：只允許 http/https；主機解析後的每個 IP 都必須是公網位址；
  實際連線釘選到已驗證的 IP（Host header + TLS SNI 保留原主機名），
  避免 DNS rebinding；不跟隨重導向；短 timeout；大小上限。
- 儲存型 XSS：下載內容必須是可辨識的點陣圖，經 photo_service 重新編碼為
  JPEG 後才儲存，副檔名一律 .jpg（不採用 URL 的副檔名）。

錯誤契約：失敗一律 raise ValidationError。
"""

import io
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

import httpx
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from books.services.photo_service import validate_and_process

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_PORTS = {"http": 80, "https": 443}
ALLOWED_IMAGE_FORMATS = ("JPEG", "PNG", "GIF", "WEBP")
MAX_COVER_BYTES = 5 * 1024 * 1024
TIMEOUT_SECONDS = 5


def _make_client():
    # trust_env=False：不吃環境的 proxy 設定，確保連線目標就是已驗證的 IP
    return httpx.Client(
        timeout=TIMEOUT_SECONDS, follow_redirects=False, trust_env=False
    )


def _is_public(ip_str):
    ip = ipaddress.ip_address(ip_str.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _resolve_public_ip(host, port):
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as e:
        raise ValidationError("無法解析封面網址的主機。") from e

    ips = sorted({info[4][0] for info in infos})
    if not ips:
        raise ValidationError("無法解析封面網址的主機。")
    for ip in ips:
        if not _is_public(ip):
            raise ValidationError("封面網址指向不允許的位址。")
    return ips[0]


def download_cover(url):
    """下載封面原始位元組（已做 SSRF 防護與大小限制）。"""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as e:
        raise ValidationError("封面網址格式不正確。") from e

    scheme = parts.scheme.lower()
    host = parts.hostname
    if scheme not in ALLOWED_SCHEMES or not host:
        raise ValidationError("封面網址只接受 http / https。")
    if parts.username or parts.password:
        raise ValidationError("封面網址不可包含帳號密碼。")

    port = port or DEFAULT_PORTS[scheme]
    ip = _resolve_public_ip(host, port)

    ip_netloc = f"[{ip}]" if ":" in ip else ip
    target = urlunsplit(
        (scheme, f"{ip_netloc}:{port}", parts.path or "/", parts.query, "")
    )
    host_header = f"[{host}]" if ":" in host else host
    if port != DEFAULT_PORTS[scheme]:
        host_header = f"{host_header}:{port}"

    buf = bytearray()
    with _make_client() as client:
        with client.stream(
            "GET",
            target,
            headers={"Host": host_header, "Accept": "image/*"},
            extensions={"sni_hostname": host},
        ) as resp:
            if resp.status_code != 200:
                raise ValidationError(
                    f"封面下載失敗（HTTP {resp.status_code}）。"
                )
            length = resp.headers.get("Content-Length")
            if length and length.isdigit() and int(length) > MAX_COVER_BYTES:
                raise ValidationError("封面檔案過大。")
            for chunk in resp.iter_bytes():
                buf.extend(chunk)
                if len(buf) > MAX_COVER_BYTES:
                    raise ValidationError("封面檔案過大。")
    return bytes(buf)


def process_cover_bytes(data, filename):
    """驗證位元組是點陣圖，重新編碼為 JPEG；回傳 .jpg 的 ImageFile。"""
    try:
        with Image.open(io.BytesIO(data), formats=ALLOWED_IMAGE_FORMATS) as img:
            img.verify()
    except Exception as e:
        raise ValidationError("封面不是有效的圖片。") from e

    upload = SimpleUploadedFile(filename, data, content_type="image/jpeg")
    return validate_and_process(upload)


def fetch_cover_image(url, basename):
    """下載並處理封面，回傳可直接存入 ImageField 的 .jpg 檔案。"""
    return process_cover_bytes(download_cover(url), f"{basename}.jpg")
