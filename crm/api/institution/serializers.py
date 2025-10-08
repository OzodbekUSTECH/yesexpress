from django.db import transaction
from rest_framework import serializers

from address.models import Address
from base.enums import DayOfWeekChoices
from courier.models import InstitutionDeliverySettings
from crm.api.address.serializers import CrmInstitutionAddressSerializer
from crm.api.institution.services import create_institution_default_schedule
from crm.api.user.serializers import CrmInstitutionUserSerializer
from institution.models import (
    Institution,
    InstitutionCategory,
    InstitutionBranch,
    InstitutionBranchSchedule,
)
from drf_extra_fields.fields import Base64ImageField

from product.models import ProductToBranch


class CrmInstitutionBranchScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstitutionBranchSchedule
        fields = ["id", "day_of_week", "start_time", "end_time", "is_active"]


class CrmInstitutionDeliverySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstitutionDeliverySettings
        fields = ["min_distance", "min_delivery_price", "price_per_km"]


class CrmInstitutionCategorySerializer(serializers.ModelSerializer):
    image_upload = Base64ImageField(source="image", write_only=True, required=True)

    class Meta:
        model = InstitutionCategory
        fields = ["id", "title_ru", "title_uz", "title_en", "position", "image", "image_upload"]


class CrmInstitutionBranchSerializer(serializers.ModelSerializer):
    address = CrmInstitutionAddressSerializer(required=True)

    class Meta:
        model = InstitutionBranch
        fields = [
            "id",
            "name",
            "institution",
            "address",
            "is_open",
            "start_time",
            "end_time",
            "is_active",
            "telegram_id_str",
        ]

    # def validate(self, attrs):
    #     institution = attrs['institution']
    #     address = Address(longitude=attrs['address']['longitude'], latitude=attrs['latitude'])
    #     if institution.region.center:
    #         distance = calculate_distance(address, institution.region.center)
    #         if distance < institution.region.radius:
    #             return True
    #     return super().validate(attrs)


class CrmInstitutionBranchDetailSerializer(CrmInstitutionBranchSerializer):
    schedule_days = CrmInstitutionBranchScheduleSerializer(many=True)
    package_vat = serializers.SerializerMethodField()

    class Meta:
        model = InstitutionBranch
        fields = [
            "id",
            "name",
            "legal_name",
            "inn",
            "pinfl",
            "phone_number",
            "institution",
            "address",
            "start_time",
            "end_time",
            "is_open",
            "is_active",
            "is_available",
            "telegram_id_str",
            "min_order_amount",
            "min_preorder_minutes",
            "max_preorder_days",
            "payme_id",
            "payme",
            "package_addition_amount",
            "package_amount",
            "package_spic_id",
            "package_code",
            "package_vat",
            "is_telegram_orders_enabled",
            "is_pickup_available",
            "specific_couriers",
            "use_auto_dispatcher",
            "schedule_days",
            "region_branch",
        ]
    
    def get_package_vat(self, obj):
        return True if obj.package_vat == 12 else False


class CrmInstitutionBranchCreateSerializer(serializers.ModelSerializer):
    address = CrmInstitutionAddressSerializer(required=True)
    package_vat = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = InstitutionBranch
        fields = [
            "id",
            "name",
            "legal_name",
            "inn",
            "pinfl",
            "phone_number",
            "institution",
            "address",
            "start_time",
            "end_time",
            "is_open",
            "is_active",
            "is_available",
            "telegram_id_str",
            "min_order_amount",
            "min_preorder_minutes",
            "max_preorder_days",
            "payme_id",
            "payme",
            "package_addition_amount",
            "package_amount",
            "package_spic_id",
            "package_code",
            "package_vat",
            "is_telegram_orders_enabled",
            "is_pickup_available",
            "specific_couriers",
            "use_auto_dispatcher",
            "region_branch",
        ]

    def create(self, validated_data):
        address_data = validated_data.pop("address", None)
        region = validated_data.get("region_branch", None)

        with transaction.atomic():
            vat_bool = validated_data.pop("package_vat", None)
            institution_branch = super().create(validated_data)
            address = Address.objects.create(region=region, **address_data)
            institution_branch.address = address
            if vat_bool is not None:
                institution_branch.vat = 12 if vat_bool else 0
            institution_branch.save()
            create_institution_default_schedule(institution_branch)
            products = institution_branch.institution.product_set.all()
            product_to_branch = []
            for product in products:
                product_to_branch.append(ProductToBranch(
                    product=product,
                    institution_branches=institution_branch,
                    is_available=True
                ))
            ProductToBranch.objects.bulk_create(product_to_branch)
        return institution_branch

    def update(self, instance, validated_data):
        address_data = validated_data.pop("address", None)
        vat_bool = validated_data.pop("package_vat", None)
        with transaction.atomic():
            timeline = instance.schedule_days.all()
            for time in timeline:
                time.start_time = validated_data.get('start_time')
                time.end_time = validated_data.get('end_time')
                time.save()
            
            institution_branch: InstitutionBranch = super().update(instance, validated_data)
            if vat_bool is not None:
                institution_branch.package_vat = 12 if vat_bool else 0
                institution_branch.save()


            if institution_branch.address is None:
                address = Address.objects.create(region=validated_data['region_branch'], **address_data)
                institution_branch.address = address

            if address_data:
                for attr, value in address_data.items():
                    setattr(institution_branch.address, attr, value)
                    institution_branch.address.save()
        return institution_branch


class CrmInstitutionBranchScheduleUpdate(serializers.Serializer):
    days_of_week = serializers.ListField(child=serializers.CharField(), required=True)
    start_time = serializers.TimeField(required=True)
    end_time = serializers.TimeField(required=True)

    def validate_days_of_week(self, value):
        for item in value:
            if item not in DayOfWeekChoices.values:
                raise serializers.ValidationError(
                    detail={"days_of_week": "Указан неправильный день недели"}
                )
        return value


class CrmInstitutionSerializer(serializers.ModelSerializer):
    is_active_status = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "legal_name",
            "logo",
            "image",
            "is_active",
            "is_open",
            "is_available",
            "is_active_status",
        ]

    def get_is_active_status(self, obj):
        return "Активно" if obj.is_active else "Неактивно"


class CrmInstitutionDetailSerializer(serializers.ModelSerializer):
    is_active_status = serializers.SerializerMethodField()
    
    # address = CrmInstitutionAddressSerializer(read_only=True)
    category = CrmInstitutionCategorySerializer(read_only=True)
    owner = CrmInstitutionUserSerializer(read_only=True)
    admin = CrmInstitutionUserSerializer(read_only=True)
    secondary_categories = CrmInstitutionCategorySerializer(many=True)
    branches = CrmInstitutionBranchSerializer(many=True)
    
    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "legal_name",
            "logo",
            "inn",
            "pinfl",
            "image",
            "description_ru",
            "description_uz",
            "description_en",
            "position",
            "category",
            "admin",
            "owner",
            "phone_number",
            # 'start_time',
            # 'end_time',
            "type",
            "delivery_by_own",
            "balance",
            "tax_percentage_ordinary",
            "min_delivery_time",
            "max_delivery_time",
            "free_delivery",
            "is_popular",
            "is_available",
            "is_active",
            "is_holding",
            "is_active_status",
            "cash",
            "payme",
            # 'address',
            "secondary_categories",
            "branches",
        ]

    def get_is_active_status(self, obj):
        return "Активно" if obj.is_active else "Неактивно"

class NullableIntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if data in ("", None):
            return None
        return super().to_internal_value(data)
class CrmInstitutionCreateSerializer(serializers.ModelSerializer):
    image_upload = Base64ImageField(source="image", write_only=True)
    logo_upload = Base64ImageField(source="logo", write_only=True, required=False, allow_null=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    logo_url = serializers.SerializerMethodField(read_only=True)
    position = NullableIntegerField(required=False, allow_null=True, default=None)


    secondary_categories = serializers.PrimaryKeyRelatedField(
        queryset=InstitutionCategory.objects.all(),
        many=True,
        required=False,
        allow_null=True,
        default=[],
    )

    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "legal_name",
            "logo",
            "logo_upload",
            "logo_url",
            "image",
            "image_upload",
            "image_url",
            "description_ru",
            "description_uz",
            "description_en",
            "position",
            "category",
            "admin",
            "owner",
            "phone_number",
            "type",
            "delivery_by_own",
            "tax_percentage_ordinary",
            "min_delivery_time",
            "max_delivery_time",
            "free_delivery",
            "is_popular",
            "is_available",
            "is_holding",
            "is_active",
            "is_open",
            "cash",
            "payme",
            "inn",
            "pinfl",
            "secondary_categories",
        ]
        # extra_kwargs = {'logo': {'read_only': True}, 'image': {'read_only': True}}

    def get_image_url(self, obj):
        if obj.image:
            return self.context["request"].build_absolute_uri(obj.image.url)
        return None

    def get_logo_url(self, obj):
        if obj.logo:
            return self.context["request"].build_absolute_uri(obj.logo.url)
        return None
    
    