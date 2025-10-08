from crm.api.promo_code.serializers import CrmPromoCodeSerializer
from order.promo_codes.models import PromoCodeUsage
from order.promo_codes.serializers import PromoCodeInfoSerializer
from order.serializers import OrderItemGroupSerializer
from rest_framework import serializers
from rest_framework.exceptions import (
    NotFound,
    ValidationError,
    APIException,
    PermissionDenied,
)
from rest_framework.authtoken.models import Token as DRFAuthToken
from address.models import Address
from courier.models import DeliverySettings
from institution.models import Institution
from order.models import Order
from user.models import User
from user.services import check_otp, send_otp_sms
from .models import Courier
from django.conf import settings


class AddressCoordinates(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["latitude", "longitude", "street", "floor", "flat_number", "reference_point"]


class DeliveringPriceCalculatorSerializer(serializers.Serializer):
    address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())
    institution = serializers.PrimaryKeyRelatedField(queryset=Institution.objects.all())


class AvailableOrdersSerializer(serializers.ModelSerializer):
    institution_name = serializers.SerializerMethodField()
    address_to = AddressCoordinates(source="address")
    address_from = serializers.SerializerMethodField()
    institution_phone_number = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_phone_number = serializers.CharField(source="customer.phone_number", allow_null=True)

    delivery_time = serializers.SerializerMethodField()
    prices = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            "id",
            "institution_name",
            "products_sum",
            "delivering_sum",
            "prices",
            "status",
            "updated_at",
            "payment_method",
            "address_to",
            "address_from",
            "institution_phone_number",
            "customer_phone_number",
            "customer_name",
            "status",
            "preparing_time",
            "delivery_time",
        ]

    def get_customer_name(self, obj):
        name = ""
        if obj.customer:
            if obj.customer.first_name:
                name = obj.customer.first_name
            if obj.customer.last_name:
                name +=f" {obj.customer.last_name}"
        return name.strip()
        
    def get_prices(self, obj):
        promocode = 0
        try:
            promo = PromoCodeUsage.objects.select_related("promo_code").get(order=obj, user=obj.customer)
            if promo:
                promocode = promo.promo_code.sum
        except PromoCodeUsage.DoesNotExist:
            pass
        price_info = {
            "discount_amount":  promocode,
            "delivery_amount":  obj.delivering_sum,
            
            "product_amount": obj.products_sum,
            "total_amount": obj.delivering_sum + obj.products_sum - promocode
        }
        return price_info
    
    def get_delivery_time(self, obj):
        item_groups = obj.item_groups.first()
        if item_groups:
            return {
                "min": item_groups.institution.min_delivery_time,
                "max": item_groups.institution.max_delivery_time
            }
        return None
    
    def get_institution_name(self, obj: Order):
        item_groups = obj.item_groups.first()
        branch = item_groups.institution_branch

        if branch:
            return branch.name
        return item_groups.institution.name
    
    def get_institution_phone_number(self, obj: Order):
        item_groups = obj.item_groups.first()
        branch = item_groups.institution_branch
        if branch:
            return branch.phone_number
        return item_groups.institution.phone_number

    def get_address_from(self, obj: Order):
        item_groups = obj.item_groups.first()
        branch = item_groups.institution_branch
        
        if branch:
            longitude = branch.address.longitude
            latitude = branch.address.latitude
            street = branch.address.street
            return {"longitude": longitude, "latitude": latitude, "street": street}
        
        return {"longitude": None, "latitude": None, "street": None}


class DeliverySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverySettings
        fields = "__all__"


class CourierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Courier
        fields = ['transport', 'car_info', 'registration_number', 'status', 'thermal_bag_number']

class PhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate(self, attrs):
        data: PhoneNumberSerializer = super().validate(attrs)
        phone_number = data["phone_number"]

        try:
            user = User.objects.get(phone_number=phone_number, courier__isnull=False)
        except User.DoesNotExist:
            raise NotFound({"message": "User dose not exist"})
        courier: Courier = user.courier
        if courier.status == Courier.Status.INACTIVE.value:
            raise APIException({"message": "User is inactive"}, code=445)

        if settings.DEBUG:
            success = True
        else:
            success = send_otp_sms(user)
        if not success:
            raise PermissionDenied(detail="error")
        return data


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    sms_code = serializers.IntegerField()

    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            user = User.objects.select_related("auth_token").get(phone_number=data["phone_number"])
        except User.DoesNotExist:
            raise NotFound({"detail": "the phone number is not correct"})
        if not check_otp(user, data["sms_code"]):
            raise ValidationError({"detail": "the otp is not correct"})

        DRFAuthToken.objects.get_or_create(user=user)  # creating user auth token if not exists
        data["user"] = user
        return data
