import json

import pytest
from django.template.loader import get_template
from django.test import Client, override_settings
from django.urls import reverse


@pytest.mark.django_db
def test_health_check_returns_database_status():
    client = Client()
    response = client.get(reverse("health_check"))

    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"


@pytest.mark.parametrize("template_name", ["403.html", "404.html", "500.html"])
def test_custom_error_templates_are_loadable(template_name):
    template = get_template(template_name)

    assert template is not None


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
def test_custom_404_page_renders():
    client = Client()
    response = client.get("/definitely-missing/")

    assert response.status_code == 404
    assert "找不到你要的頁面" in response.content.decode("utf-8")
