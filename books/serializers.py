from rest_framework import serializers
from books.models.official_book import OfficialBook

class OfficialBookSerializer(serializers.ModelSerializer):
    # We'll add Author and Publisher details here if needed, 
    # but for now let's keep it simple and expand as we verify.
    
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
            "description"
        ]
        read_only_fields = ["id"]
