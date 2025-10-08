from typing import Dict, Any

from django.contrib.auth import get_user_model, authenticate
from crm.api.promo_code.serializers import CrmPromoCodeSerializer
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import ValidationError
from django.db import IntegrityError
from base.serializer import get_phone_number_field
from django.db.models import Q

User = get_user_model()


class CustomTokenObtainSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
        }
        user = User.objects.filter(**authenticate_kwargs).first()
        if user is None:
            raise AuthenticationFailed("User does not exist!")
        password = attrs["password"]
        if not user.check_password(password):
            raise AuthenticationFailed("Incorrect password!")
        authenticate_kwargs["password"] = password

        self.user = authenticate(**authenticate_kwargs)

        if not self.user:
            raise AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            )

        data = super().validate(attrs)
        data["user_data"] = CrmUserSerializer(user, context=self.context).data
        return data


class CrmUserSerializer(serializers.ModelSerializer):
    phone_number = get_phone_number_field()
    promo_codes = serializers.SerializerMethodField()
    closed_orders = serializers.IntegerField(read_only=True)
    rejected_orders = serializers.IntegerField(read_only=True)
    total_orders = serializers.IntegerField(read_only=True)
    total_sum = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = User
        fields = ["id", "phone_number", "first_name", "last_name", "email", "type", "password", "date_joined", "promo_codes", "closed_orders", "rejected_orders", "total_orders", "total_sum"]
        extra_kwargs = {"password": {"write_only": True}}
        
    def get_promo_codes(self, user):
        return CrmPromoCodeSerializer(
            user.used_promo_codes.filter(
                Q(users__isnull=True) | Q(users=user)
            ).distinct(),
            many=True
        ).data

    def create(self, validated_data):
        try:
            user = User(
                phone_number=validated_data["phone_number"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                email=validated_data["email"],
                type=validated_data["type"],
            )
            user.set_password(validated_data["password"])
            user.save()
            return user
        except IntegrityError as e:
            if "phone_number" in str(e):
                raise ValidationError({"phone_number": "This phone number is already registered."})
            else:
                raise e


class CrmUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "type", 'phone_number']

class CrmInstitutionUserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number", "password", "password2"]
        extra_kwargs = {"password": {"write_only": True}, "phone_number": {"validators": []} }

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("Passwords dont math")
        return attrs
    
    def validate_phone_number(self, value):
        user = User.objects.filter(phone_number=value)
        if user.exists():
            return value
        return value

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        phone_number = validated_data.get("phone_number")
        user = User.objects.filter(phone_number=phone_number)
        if not user.exists():
            user = User.objects.create(**validated_data)
        user.first_name = validated_data['first_name']
        user.last_name = validated_data['last_name']
        user.email = validated_data['email']

        user.set_password(password)
        user.save()
        return user


class CrmInstitutionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number"]


class CrmInstitutionChangePasswordSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("Passwords dont math")
        return attrs

    class Meta:
        model = User
        fields = ["password", "password2"]

    def update(self, instance, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        instance.set_password(password)
        instance.save()
        return instance
