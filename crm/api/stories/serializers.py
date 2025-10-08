from rest_framework import serializers

from address.models import Region
from base.serializer import Base64FileField
from crm.api.address.serializers import CrmRegionSerializer
from crm.api.user.serializers import CrmUserSerializer
from institution.models import Institution
from institution.serializers import InstitutionMiniSerializer
from stories.models import Stories


class CrmStoriesSerializer(serializers.ModelSerializer):
    file_type = serializers.SerializerMethodField(read_only=True)
    # created_user = CrmUserSerializer()
    regions = serializers.SerializerMethodField(read_only=True)
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
            "file_type",
            "url_link",
            "start_date",
            "end_date",
            "is_active",
            "position",
            "created_at",
            "created_user",
            "regions",
        ]
        # read_only_fields = ["file_type", "created_at", "created_user"]
        read_only_fields = ["file_type", "created_at"]

    def get_file_type(self, obj: Stories):
        file_name = obj.image_stories_ru.name
        file_type = "unknown"
        if (
            file_name.endswith(".jpg")
            or file_name.endswith(".jpeg")
            or file_name.endswith(".png")
            or file_name.endswith(".gif")
        ):
            file_type = "image"
        else:
            file_type = "video"
        return file_type

    def get_regions(self, obj: Stories):
        return CrmRegionSerializer(instance=obj.get_related_regions(), many=True).data


class CrmStoriesCreateSerializer(serializers.ModelSerializer):
    image_stories_ru = Base64FileField(required=True)
    image_stories_en = Base64FileField(required=True)
    image_stories_uz = Base64FileField(required=True)
    logo_stories_ru = Base64FileField(required=True)
    logo_stories_en = Base64FileField(required=True)
    logo_stories_uz = Base64FileField(required=True)
    region_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    institution = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all(),
        write_only=True,
    )
    institution_data = InstitutionMiniSerializer(
        source="institution",
        read_only=True,
    )

    def validate_regions_ids(self, value):
        existing_regions = Region.objects.values_list("id", flat=True)
        for region_id in value:
            if region_id not in existing_regions:
                raise serializers.ValidationError(f"Региона с id {region_id} не существует")
        return value

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
            "url_link",
            "start_date",
            "end_date",
            "is_active",
            "position",
            "created_at",
            "created_user",
            "region_ids",
            "institution",
            "institution_data",
        ]
        read_only_fields = ["file_type", "created_at", "created_user"]
