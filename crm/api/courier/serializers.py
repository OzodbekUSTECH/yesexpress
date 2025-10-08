from django.contrib.auth import get_user_model
from rest_framework import serializers

from base.serializer import DynamicFieldsModelSerializer
from courier.models import Courier, DeliverySettings

from crm.api.user.serializers import CrmUserSerializer, CrmUserUpdateSerializer

User = get_user_model()


class CrmDeliverySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverySettings
        fields = ["min_distance", "min_delivery_price", "price_per_km"]


class CrmCourierSerializer(DynamicFieldsModelSerializer):
    user = CrmUserSerializer()

    class Meta:
        model = Courier
        fields = [
            "id",
            "user",
            "passport_series",
            "transport",
            "balance",
            "status",
            "car_info",
            "registration_number",
            "thermal_bag_number",
        ]
        read_only_fields = ["id", "balance"]

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = User.objects.filter(phone_number=user_data["phone_number"]).first()
        if user:
            courier = Courier.objects.filter(user=user).first()
            user.first_name=user_data["first_name"]
            user.last_name=user_data["last_name"]
            user.email=user_data["email"]
            user.set_password(user_data["password"])
            user.save()
        else:
            user = User(
                phone_number=user_data["phone_number"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                email=user_data["email"],
            )
            user.set_password(user_data["password"])
            user.save()
            courier = Courier.objects.create(**validated_data, user=user)
            
        return courier


class CrmCourierUpdateSerializer(serializers.ModelSerializer):
    user = CrmUserUpdateSerializer()
    
    class Meta:
        model = Courier
        fields = [
            "id",
            "user",
            "passport_series",
            "transport",
            "status",
            "car_info",
            "balance",
            "registration_number",
            "thermal_bag_number",
        ]

    
    def update(self, instance, validated_data):
        
        user_data = validated_data.pop("user", None)

        # ⚡️ Nested user update
        if user_data:
            user_serializer = CrmUserUpdateSerializer(
                instance=instance.user,
                data=user_data,
                partial=True  # bu orqali faqat o‘zgarayotgan maydonlar tekshiriladi
            )
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

        # Courier modelini update qilish
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance