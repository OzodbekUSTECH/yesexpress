from rest_framework import serializers
from rest_framework_gis import serializers as gis_serializers
from address.models import Address, Region

from common.serializer import fields as common_fields


class CrmInstitutionAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "street", "reference_point", "latitude", "longitude"]


class CrmRegionSerializer(serializers.ModelSerializer):
    polygon = common_fields.GisFieldCustom()

    class Meta:
        model = Region
        fields = ["id", "name", "polygon"]

    # пока что в комментарии
    #
    # def create(self, validated_data):
    #     address_data = validated_data.pop('center', None)
    #
    #     region = super().create(validated_data)
    #     center = Address.objects.create(region=region, **address_data)
    #     region.center = center
    #     region.save()
    #     return region
    #
    #
    # def update(self, instance, validated_data):
    #     address_data = validated_data.pop('center', None)
    #
    #     with transaction.atomic():
    #         institution: Institution = super().update(instance, validated_data)
    #
    #         if address_data and instance.center:
    #             for attr, value in address_data.items():
    #                 setattr(instance.center, attr, value)
    #                 instance.center.save()
    #     return institution
