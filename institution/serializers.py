from datetime import datetime
from common.models import Settings
from rest_framework import serializers

from address.models import Address
from address.serializers import InstitutionAddressSerializer
from courier.models import InstitutionDeliverySettings
from courier.services import get_delivery_settings
from order.exceptions import CantFindSuitableBranchError
from order.services import calculate_delivering_sum
from rkeeper.services import rkeeperAPI
from .models import (
    Institution,
    InstitutionCategory,
    LikedInstitutions,
    InstitutionBranchSchedule,
)
from base.enums import DayOfWeekChoices
from product.serializers import CategoryListSerializer, ThumbnailSerializer, ProductListSerializer
from .services import find_another_branch, find_suitable_branch


class DeliverySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstitutionDeliverySettings
        fields = "__all__"


class InstitutionCategoryListSerializer(serializers.ModelSerializer):

    class Meta:
        model = InstitutionCategory
        fields = ["id", "title_ru", "title_uz", "title_en", "icon", "image"]


class InstitutionListSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._delivery_settings = get_delivery_settings()

    rating = serializers.ReadOnlyField()
    is_liked = serializers.SerializerMethodField()
    is_open_by_schedule = serializers.BooleanField()
    has_active_branch = serializers.BooleanField()
    category = InstitutionCategoryListSerializer()
    image = ThumbnailSerializer("small")
    logo = ThumbnailSerializer("logo")
    address = InstitutionAddressSerializer(allow_null=True)
    delivery_price = serializers.IntegerField(allow_null=True, default=None)
    min_order_amount = serializers.IntegerField(allow_null=True, default=None)
    package_addition_amount = serializers.IntegerField(allow_null=True, default=None)
    package_amount = serializers.IntegerField(allow_null=True, default=None)

    class Meta:
        model = Institution
        exclude = [
            "admin",
            "description",
            "description_i18n",
            "type",
            "i18n",
            "owner",
            "balance",
            "tax_percentage_ordinary",
            "secondary_categories",
            "free_delivery",
            "payme",
            "cash"
        ]


    def to_representation(self, instance):
        lat = self.context.get("lat")
        long = self.context.get("long")
        address = self.context.get("address")
        if not lat or not long:
            return super().to_representation(instance)

        if not address:
            address = Address(latitude=lat, longitude=long)
        if address:
            try:
                weekday = DayOfWeekChoices.get_value_by_number(datetime.now().weekday())
                branch = find_suitable_branch(instance, address)
                
                if not branch:
                    is_open_by_schedule = False
                    branch = find_another_branch(instance, address)
                else:
                    is_open_by_schedule = branch.is_open_by_schedule
                               
                schedule = InstitutionBranchSchedule.objects.get(institution=branch, day_of_week=weekday)

                delivery_settings = self._delivery_settings
                if instance.delivery_by_own:
                    delivery_settings = getattr(instance, "delivery_settings", None)

                delivery_price = int(
                    calculate_delivering_sum(
                        instance, address, branch=branch, global_delivery_settings=delivery_settings
                    )
                )
                instance.address = branch.address
                instance.delivery_price = delivery_price
                instance.start_time = schedule.start_time
                instance.end_time = schedule.end_time
                instance.is_open_by_schedule = is_open_by_schedule
                instance.min_order_amount = branch.min_order_amount
                instance.package_addition_amount = branch.package_addition_amount
                instance.package_amount = branch.package_amount
                
                if branch.is_open == False or schedule.is_active == False:
                    instance.is_open = False
                    if getattr(instance, "has_active_branch"):
                        setattr(instance, "has_active_branch", False)
                    
                if getattr(instance, "has_active_branch", False):
                    instance.is_available = True
                    
            except InstitutionBranchSchedule.DoesNotExist:
                print("No schedule found for", instance.name, instance.start_time, instance.end_time)
            except CantFindSuitableBranchError:
                print("CantFindSuitableBranchError", instance.name, instance.start_time, instance.end_time)
                pass
        return super().to_representation(instance)

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return LikedInstitutions.objects.filter(institution=obj, customer=request.user).exists()
        return False


class InstitutionSearchSerializer(InstitutionListSerializer):
    product_set = ProductListSerializer(many=True, read_only=True)


class InstitutionDetailSerializer(InstitutionListSerializer):
    category_set = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    min_order_amount = serializers.SerializerMethodField()
    package_addition_amount = serializers.SerializerMethodField()
    package_amount = serializers.SerializerMethodField()

    def get_min_order_amount(self, obj):
        point = self.context.get("point")
        address = Address(point)
        branch = find_suitable_branch(obj, address)

        return branch.min_order_amount if branch else None
    
    def get_package_amount(self, obj):
        point = self.context.get("point")
        address = Address(point)
        branch = find_suitable_branch(obj, address)
        return branch.package_amount if branch else None
    
    def get_package_addition_amount(self, obj):
        point = self.context.get("point")
        address = Address(point)
        branch = find_suitable_branch(obj, address)
        return branch.package_addition_amount if branch else None
    
    def get_payment_method(self, obj):
        common_payment = Settings.objects.filter().first()
        if not common_payment:
            return {"cash": obj.cash, "payme": obj.payme}

        cash = common_payment.cash_payment_avaible and obj.cash
        payme = common_payment.payme_payment_avaible and obj.payme

        return {"cash": cash, "payme": payme}
            
        
    def get_category_set(self, obj):
        active_categories = self.context.get("active_categories")
        if active_categories is not None:
            return CategoryListSerializer(active_categories, many=True, context=self.context).data
        return CategoryListSerializer(obj.category_set.filter(is_active=True).all(), many=True, context=self.context).data

    def get_is_liked(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False

        return LikedInstitutions.objects.filter(customer=user, institution=obj).exists()

class InstitutionCategoryDetailSerializer(CategoryListSerializer):
    institution_set = InstitutionListSerializer(many=True, read_only=True)

    class Meta:
        model = InstitutionCategory
        fields = ["id", "title_ru", "title_uz", "title_en", "institution_set"]


class InstitutionMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ["id", "name", "logo"]
