"""
年齡驗證 Validator 測試。

測試 BR-11: 年滿 18 歲以上之成年人，方能註冊使用本系統及服務。
"""

from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError

from accounts.validators import (
    calculate_age,
    is_adult,
    validate_age_18_or_older,
)


class TestValidateAge18OrOlder:
    """測試 validate_age_18_or_older 函式"""

    def test_exact_18_years_old_passes(self):
        """剛好 18 歲應該通過驗證"""
        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day)
        # 不應該拋出異常
        validate_age_18_or_older(birth_date)

    def test_18_years_minus_one_day_fails(self):
        """差一天滿 18 歲應該失敗"""
        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day) + timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            validate_age_18_or_older(birth_date)
        assert exc_info.value.code == "underage"

    def test_17_years_old_fails(self):
        """17 歲應該失敗"""
        today = date.today()
        birth_date = date(today.year - 17, today.month, today.day)
        with pytest.raises(ValidationError) as exc_info:
            validate_age_18_or_older(birth_date)
        assert exc_info.value.code == "underage"

    def test_30_years_old_passes(self):
        """30 歲應該通過驗證"""
        today = date.today()
        birth_date = date(today.year - 30, today.month, today.day)
        validate_age_18_or_older(birth_date)

    def test_none_value_passes(self):
        """None 值應該通過（不驗證）"""
        validate_age_18_or_older(None)

    def test_leap_year_birthday(self):
        """閏年出生的測試"""
        today = date.today()
        # 如果今天不是 2/29，用 3/1 計算
        birth_date = date(today.year - 18, 3, 1)
        validate_age_18_or_older(birth_date)


class TestCalculateAge:
    """測試 calculate_age 函式"""

    def test_exact_age(self):
        """測試精確年齡計算"""
        today = date.today()
        birth_date = date(today.year - 25, today.month, today.day)
        assert calculate_age(birth_date) == 25

    def test_age_before_birthday(self):
        """生日前的年齡計算"""
        today = date.today()
        # 假設生日在下個月
        next_month = today.month + 1 if today.month < 12 else 1
        birth_year = today.year - 25 if today.month < 12 else today.year - 24
        birth_date = date(birth_year, next_month, min(today.day, 28))
        # 年齡應該是 24（因為今年生日還沒到）
        assert calculate_age(birth_date) == 24

    def test_age_after_birthday(self):
        """生日後的年齡計算"""
        today = date.today()
        # 假設生日在上個月
        prev_month = today.month - 1 if today.month > 1 else 12
        birth_year = today.year - 25 if today.month > 1 else today.year - 26
        birth_date = date(birth_year, prev_month, min(today.day, 28))
        # 年齡應該是 25（因為今年生日已過）
        assert calculate_age(birth_date) == 25

    def test_none_returns_zero(self):
        """None 應該返回 0"""
        assert calculate_age(None) == 0


class TestIsAdult:
    """測試 is_adult 函式"""

    def test_18_is_adult(self):
        """18 歲是成年人"""
        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day)
        assert is_adult(birth_date) is True

    def test_17_is_not_adult(self):
        """17 歲不是成年人"""
        today = date.today()
        birth_date = date(today.year - 17, today.month, today.day)
        assert is_adult(birth_date) is False

    def test_30_is_adult(self):
        """30 歲是成年人"""
        today = date.today()
        birth_date = date(today.year - 30, today.month, today.day)
        assert is_adult(birth_date) is True

    def test_boundary_case(self):
        """邊界案例：差一天滿 18 歲"""
        today = date.today()
        birth_date = date(today.year - 18, today.month, today.day) + timedelta(days=1)
        assert is_adult(birth_date) is False
