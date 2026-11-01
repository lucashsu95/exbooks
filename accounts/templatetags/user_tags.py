from django import template
from django.contrib.auth.models import AbstractBaseUser

from accounts.services.display_name_service import display_name_for

register = template.Library()


@register.filter
def display_name(user: AbstractBaseUser | None) -> str:
    """
    他人顯示名稱：暱稱，空白時「會員#<pk>」，絕不顯示 email。

    用法：{% load user_tags %}{{ deal.applicant|display_name }}
    """
    return display_name_for(user)
