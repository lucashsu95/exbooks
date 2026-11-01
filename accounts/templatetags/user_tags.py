from django import template

from accounts.models import user_display_name

register = template.Library()


@register.filter
def display_name(user) -> str:
    """
    他人顯示名稱：暱稱，空白時「會員#<pk>」，絕不顯示 email。

    用法：{% load user_tags %}{{ deal.applicant|display_name }}
    """
    return user_display_name(user)
