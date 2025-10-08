from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from base.serializer import DynamicFieldsModelSerializer, get_phone_number_field
from crm.api.courier.serializers import CrmCourierSerializer
from institution.models import InstitutionBranch, InstitutionBranchWorker
from order.models import Order


User = get_user_model()


class RestaurantUserCreateSerializer(serializers.Serializer):
    phone_number = get_phone_number_field()
    first_name = serializers.CharField()
    last_name = serializers.CharField(required=False, allow_null=True)
    password = serializers.CharField()
    institution_branch = serializers.PrimaryKeyRelatedField(queryset=InstitutionBranch.objects.all(), write_only=True)

    def create(self, validated_data):
        institution_branch = validated_data.pop('institution_branch')
        if User.objects.filter(phone_number=validated_data["phone_number"]).exists():
            raise ValidationError({"detail": "Пользователь с таким номером телефона уже существует."})
        new_user = User(
            phone_number=validated_data["phone_number"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            type='institution_worker'
        )
        new_user.set_password(validated_data["password"])
        new_user.save()
        InstitutionBranchWorker.objects.create(
            institution_branch=institution_branch,
            worker=new_user
        )
        return new_user

    class Meta:
        fields = ["id", "phone_number", "first_name", "last_name", "password", "institution_branch"]


class RestaurantUserSerializer(serializers.ModelSerializer):
    phone_number = get_phone_number_field()
    institution_branch = serializers.SerializerMethodField()

    def get_institution_branch(self, obj):
        branch = InstitutionBranchWorker.objects.filter(worker=obj).first()
        if branch:
            return branch.institution_branch.name

    class Meta:
        model = User
        fields = ["id", "phone_number", "first_name", "last_name", "email", "password", 'institution_branch']
        extra_kwargs = {"password": {"write_only": True}}


class RestaurantUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", 'phone_number']


class RestaurantInstitutionListSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region_branch.name', read_only=True)

    class Meta:
        model = InstitutionBranch
        fields = [
            "id",
            "name",
            "address",
            "is_open",
            "is_available",
            "region_name",
        ]

class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "status",
        ]


class RestaurantCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "type",
            "email",
            "first_name",
            "last_name",
        ]


class RestaurantOrderSerializer(DynamicFieldsModelSerializer):
    customer = RestaurantCustomerSerializer()
    courier = CrmCourierSerializer()
    institution_name = serializers.SerializerMethodField()
    institution_branch_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "address",
            "institution_name",
            "institution_branch_name",
            "created_at",
            "updated_at",
            "note",
            "is_paid",
            "payment_method",
            "customer",
            "products_sum",
            "delivering_sum",
            "total_sum",
            "courier",
            "receipt_id",
            "fcm_device",
            "preparing_time",
            "discount_sum",
            "is_process",
        ]

    def get_institution_name(self, obj):
        if obj.item_groups.exists():
            if obj.item_groups.first().institution is None:
                return None
            return obj.item_groups.first().institution.name
    
    def get_institution_branch_name(self, obj):
        if obj.item_groups.exists():
            if obj.item_groups.first().institution_branch is None:
                return None
            return obj.item_groups.first().institution_branch.name
        return None

class OrderActionModelSerializer(serializers.ModelSerializer):
    customer = RestaurantCustomerSerializer()
    courier = CrmCourierSerializer()

    class Meta:
        model = Order
        exclude = []
