"""
年齡驗證相關的 Validator。

BR-11: 年滿 18 歲以上之成年人，方能註冊使用本系統及服務。
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_age_18_or_older(value: date) -> None:
    """
    驗證年齡是否滿 18 歲。

    Args:
        value: 出生日期

    Raises:
        ValidationError: 如果年齡小於 18 歲
    """
    if value is None:
        return

    today = date.today()
    age = (
        today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    )

    if age < 18:
        raise ValidationError(
            _("您的年齡未滿 18 歲，依法規限制無法註冊使用本服務"),
            code="underage",
        )


def calculate_age(birth_date: date) -> int:
    """
    計算年齡。

    Args:
        birth_date: 出生日期

    Returns:
        int: 年齡（歲）
    """
    if birth_date is None:
        return 0

    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def is_adult(birth_date: date) -> bool:
    """
    檢查是否年滿 18 歲。

    Args:
        birth_date: 出生日期

    Returns:
        bool: True 如果年滿 18 歲，否則 False
    """
    return calculate_age(birth_date) >= 18
