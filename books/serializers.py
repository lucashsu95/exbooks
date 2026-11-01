from rest_framework import serializers

from accounts.serializers import DisplayNameField
from books.models.official_book import OfficialBook
from books.models.shared_book import SharedBook


class OfficialBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficialBook
        fields = [
            "id",
            "isbn",
            "title",
            "author",
            "publisher",
            "category",
            "cover_image",
            "description",
        ]
        read_only_fields = ["id"]


class SharedBookSerializer(serializers.ModelSerializer):
    official_book = OfficialBookSerializer(read_only=True)
    owner_nickname = DisplayNameField(source="owner")
    keeper_nickname = DisplayNameField(source="keeper")

    class Meta:
        model = SharedBook
        fields = [
            "id",
            "official_book",
            "owner",
            "owner_nickname",
            "keeper",
            "keeper_nickname",
            "book_set",
            "transferability",
            "status",
            "condition_description",
            "loan_duration_days",
            "extend_duration_days",
            "min_trust_level",
            "listed_at",
        ]
        # owner / keeper / book_set 只能經 service 變更（發布、交易、書套管理）
        read_only_fields = ["status", "listed_at", "owner", "keeper", "book_set"]
