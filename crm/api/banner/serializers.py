from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from banner.models import Banner


class CrmBannerSerializer(serializers.ModelSerializer):
    img_ru_upload = Base64ImageField(source="img_ru", write_only=True)
    img_uz_upload = Base64ImageField(source="img_uz", write_only=True)
    img_en_upload = Base64ImageField(source="img_en", write_only=True)
    file_type = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = (
            "img_ru",
            "img_uz",
            "img_en",
            "file_type",
            "img_ru_upload",
            "img_uz_upload",
            "img_en_upload",
            "is_active",
            "position",
            "start_date",
            "end_date",
            "title_ru",
            "title_uz",
            "title_en",
            "description_ru",
            "description_uz",
            "description_en",
            "category",
            "restaurants",
            "id",
        )
        read_only_fields = ("img_ru", "img_uz", "img_en", "file_type")

    def get_file_type(self, obj: Banner):
        file_name = obj.img_ru.name
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
