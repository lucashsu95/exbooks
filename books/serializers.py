from rest_framework import serializers
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
    owner_nickname = serializers.ReadOnlyField(source="owner.profile.nickname")
    keeper_nickname = serializers.ReadOnlyField(source="keeper.profile.nickname")

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
        read_only_fields = ["status", "listed_at"]
