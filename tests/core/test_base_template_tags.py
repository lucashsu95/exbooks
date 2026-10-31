"""base.html 內嵌 script 的 Django 標籤不可被格式化工具拆開。

曾發生 `{% if user.is_authenticated %}` 被拆成 `{` / `%` / `if ... %` / `}` 多行，
Django 不再解析，原樣輸出成 JS 造成每頁 `Unexpected token '%'`。
"""

import re
from pathlib import Path

import pytest
from django.urls import reverse

BASE_HTML = Path(__file__).resolve().parents[2] / "templates" / "base.html"


def test_base_html_has_no_split_template_tags() -> None:
    source = BASE_HTML.read_text(encoding="utf-8")
    assert not re.search(r"^\s*%\s*$", source, re.M)
    assert not re.search(r"^\s*(?:if|endif|elif|else)\b[^\n]*%\s*$", source, re.M)


@pytest.mark.django_db
def test_rendered_page_has_no_raw_template_syntax(client) -> None:
    html = client.get(reverse("landing")).content.decode()
    assert "user.is_authenticated" not in html
    assert not re.search(r"\{\s*%|%\s*\}", html)
