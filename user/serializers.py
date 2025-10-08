from order.serializers import CourierSerializer
from rest_framework import serializers

from base.serializer import get_phone_number_field
from user.models import CustomFCMDevice, User


class UserSerializer(serializers.ModelSerializer):
    token = serializers.CharField(source="auth_token.key")
    courier_id = serializers.IntegerField(source="courier.id")
    phone_number = get_phone_number_field()
    courier = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "phone_number",
            "first_name",
            "last_name",
            "email",
            "password",
            "token",
            "courier_id",
            "courier"
        ]
        extra_kwargs = {"password": {"write_only": True}, "courier": {"read_only": True}}
        read_only_fields = ["token", "courier_id", "courier"]

    def get_courier(self, obj):
        if hasattr(obj, "courier"):
            courier = CourierSerializer(obj.courier).data
            courier['car_info'] = '' if courier['car_info'] is None else courier['car_info'] 
            courier['registration_number'] = '' if courier['registration_number'] is None else courier['registration_number'] 
            return courier
        return {}


    def create(self, validated_data):
        user = User(
            phone_number=validated_data["phone_number"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class CustomFCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomFCMDevice
        fields = "__all__" 