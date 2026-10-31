"""L-7：評分滑桿不可把原始欄位值直接塞進 Alpine x-data 的 JS 運算式。"""

import html
import re

import pytest
from django.template import Context, Template

from deals.forms import RatingForm

MALICIOUS = "1};alert(1);{a:1"
XDATA_RE = re.compile(r'x-data="([^"]*)"')


def _render(data):
    form = RatingForm(data=data)
    form.is_valid()
    return Template("{% load crispy_forms_tags %}{% crispy form %}").render(
        Context({"form": form})
    )


def _rating_xdata(rendered):
    return [
        html.unescape(m)
        for m in XDATA_RE.findall(rendered)
        if "value" in m
    ]


@pytest.mark.parametrize(
    "payload",
    [MALICIOUS, "3' + alert(1) + '", '3" onmouseover="alert(1)', "</div><script>alert(1)</script>"],
)
def test_malicious_value_cannot_break_out_of_xdata(payload):
    rendered = _render(
        {
            "friendliness_score": payload,
            "punctuality_score": "4",
            "accuracy_score": "5",
        }
    )
    xdatas = _rating_xdata(rendered)
    assert len(xdatas) == 3
    for expr in xdatas:
        # 值只能出現在單引號字串字面值內，且字串中不得含未跳脫的引號
        assert re.fullmatch(
            r"\{ value: parseInt\('[^'\"<>;]*', 10\) \|\| 3 \}", expr
        ), expr
    assert "<script>alert(1)" not in rendered
    assert 'onmouseover="alert' not in rendered


def test_normal_value_still_rendered():
    rendered = _render(
        {"friendliness_score": "4", "punctuality_score": "2", "accuracy_score": "5"}
    )
    xdatas = _rating_xdata(rendered)
    assert "{ value: parseInt('4', 10) || 3 }" in xdatas


def test_unbound_form_defaults_to_three():
    rendered = Template("{% load crispy_forms_tags %}{% crispy form %}").render(
        Context({"form": RatingForm()})
    )
    assert "{ value: parseInt('3', 10) || 3 }" in _rating_xdata(rendered)
