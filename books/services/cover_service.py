"""
封面 URL 下載服務（ADR F-8）。

cover_url 來自使用者輸入，下載時必須防範：
- SSRF：只允許 http/https 且只連預設埠（80/443）；主機解析後的每個 IP
  都必須是公網位址，且不可落在會內嵌 IPv4 的 IPv6 轉譯／隧道前綴
  （NAT64、6to4、Teredo）；
  實際連線釘選到已驗證的 IP（Host header + TLS SNI 保留原主機名），
  避免 DNS rebinding；不跟隨重導向；短 timeout；大小上限。
- 儲存型 XSS：下載內容必須是 JPG / PNG（與 photo_service 相同的格式白名單），
  經 photo_service 重新編碼為 JPEG 後才儲存，檔名一律 cover_filename()
  （不採用 URL 的副檔名）。

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

from books.services.photo_service import ALLOWED_IMAGE_FORMATS, validate_and_process

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_PORTS = {"http": 80, "https": 443}
# 這些 IPv6 前綴會把任意 IPv4（含內網）包進位址裡，一律拒絕
BLOCKED_IPV6_NETWORKS = tuple(
    ipaddress.ip_network(net)
    for net in (
        "64:ff9b::/96",  # NAT64 well-known prefix (RFC 6052)
        "64:ff9b:1::/48",  # NAT64 local-use prefix (RFC 8215)
        "2002::/16",  # 6to4 (RFC 3056)
        "2001::/32",  # Teredo (RFC 4380)
    )
)
MAX_COVER_BYTES = 5 * 1024 * 1024
TIMEOUT_SECONDS = 5


def _make_client():
    # trust_env=False：不吃環境的 proxy 設定，確保連線目標就是已驗證的 IP
    return httpx.Client(
        timeout=TIMEOUT_SECONDS, follow_redirects=False, trust_env=False
    )


def _is_public(ip_str):
    ip = ipaddress.ip_address(ip_str.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        elif any(ip in net for net in BLOCKED_IPV6_NETWORKS):
            return False
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

    default_port = DEFAULT_PORTS[scheme]
    if port is not None and port != default_port:
        raise ValidationError("封面網址只接受預設埠（http 80 / https 443）。")
    port = default_port
    ip = _resolve_public_ip(host, port)

    ip_netloc = f"[{ip}]" if ":" in ip else ip
    target = urlunsplit(
        (scheme, f"{ip_netloc}:{port}", parts.path or "/", parts.query, "")
    )
    host_header = f"[{host}]" if ":" in host else host

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


def cover_filename(basename):
    """封面檔名的單一來源（一律 .jpg，見 process_cover_bytes）。"""
    return f"{basename}.jpg"


def fetch_cover_image(url, basename):
    """下載並處理封面，回傳可直接存入 ImageField 的檔案（name 為 cover_filename）。"""
    return process_cover_bytes(download_cover(url), cover_filename(basename))
