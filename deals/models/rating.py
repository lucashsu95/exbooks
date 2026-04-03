from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import BaseModel


class Rating(BaseModel):
    """
    交易評價。面交完成後雙方互評。
    評分維度：誠信、準時、書況描述準確度（各 1~5 分）。
    """

    deal = models.ForeignKey(
        "deals.Deal",
        on_delete=models.PROTECT,
        related_name="ratings",
        verbose_name="交易",
    )
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="given_ratings",
        verbose_name="評價者",
    )
    ratee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_ratings",
        verbose_name="被評價者",
    )
    friendliness_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="友善評分",
    )
    punctuality_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="準時評分",
    )
    accuracy_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="書況準確度評分",
    )
    comment = models.TextField(blank=True, verbose_name="評語")

    class Meta:
        db_table = "exbook_rating"
        verbose_name = "評價"
        verbose_name_plural = "評價"
        constraints = [
            models.UniqueConstraint(
                fields=["deal", "rater"],
                name="unique_deal_rater",
            ),
        ]

    def __str__(self):
        return f"{self.rater} → {self.ratee} ({self.deal})"

    @property
    def average_score(self):
        """計算三項評分的平均分。"""
        return (
            self.friendliness_score + self.punctuality_score + self.accuracy_score
        ) / 3
