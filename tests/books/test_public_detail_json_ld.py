"""L-9：公開詳情頁的 JSON-LD 不可被書名中的 </script> 跳脫。"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.template import Context, Template
from django.test import RequestFactory

from books.models import SharedBook
from books.views_public import public_book_detail
from tests.factories import OfficialBookFactory, SharedBookFactory

EVIL_TITLE = "</script><script>alert(1)</script>"
TEMPLATE_PATH = (
    Path(settings.BASE_DIR) / "templates" / "books" / "public" / "browse_detail.html"
)


def _json_ld_script_line():
    for line in TEMPLATE_PATH.read_text(encoding="utf-8").splitlines():
        if "application/ld+json" in line:
            return line.strip()
    raise AssertionError("browse_detail.html 找不到 JSON-LD script")


@pytest.mark.django_db
def test_json_ld_escapes_script_breakout():
    book = SharedBookFactory(
        official_book=OfficialBookFactory(title=EVIL_TITLE, description="A & B <i>"),
        status=SharedBook.Status.TRANSFERABLE,
    )
    request = RequestFactory().get(f"/browse/{book.pk}/")

    with patch("books.views_public.render") as mock_render:
        public_book_detail(request, book.pk)
    context = mock_render.call_args.args[2]

    rendered = Template(_json_ld_script_line()).render(Context(context))
    # 唯一的 </script> 只能是模板本身的結尾
    assert rendered.count("</script>") == 1
    assert "<script>alert(1)" not in rendered
    assert "<i>" not in rendered

    payload = rendered.split(">", 1)[1].rsplit("</script>", 1)[0]
    data = json.loads(payload)
    assert data["name"] == EVIL_TITLE
    assert data["description"] == "A & B <i>"
