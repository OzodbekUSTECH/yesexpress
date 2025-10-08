from rest_framework import serializers
from stories.models import Stories
from institution.serializers import InstitutionMiniSerializer


class StoriesSerializer(serializers.ModelSerializer):
    file_type = serializers.CharField(read_only=True)
    institution_data = InstitutionMiniSerializer(read_only=True, source="institution")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        logo_file_name: str = representation["image_stories_ru"]

        if (
            logo_file_name.endswith(".jpg")
            or logo_file_name.endswith(".jpeg")
            or logo_file_name.endswith(".png")
            or logo_file_name.endswith(".gif")
        ):
            representation["file_type"] = "image"
        else:
            representation["file_type"] = "video"

        return representation

    class Meta:
        model = Stories
        fields = [
            "id",
            "title",
            "image_stories_ru",
            "image_stories_en",
            "image_stories_uz",
            "logo_stories_ru",
            "logo_stories_en",
            "logo_stories_uz",
            "created_at",
            "url_link",
            "file_type",
            "institution_data",
        ]
        read_only_fields = ["file_type"]
