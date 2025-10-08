from django.contrib.auth import get_user_model
from address.models import Address
from address.serializers import AddressSerializer
from order.serializers import OrderTimelineSerializer
from product.serializers import OptionItemSerializer
from rest_framework import serializers

from base.serializer import DynamicFieldsModelSerializer
from crm.api.courier.serializers import CrmCourierSerializer
from crm.api.product.serializers import CrmOptionItemShortSerializer, CrmProductSerializer, CrmOptionItemSerializer
from crm.api.user.serializers import CrmUserSerializer
from order.models import Order, OrderItemGroup, OrderItem
from product.models import OptionItem


User = get_user_model()


class CrmCustomerSerializer(serializers.ModelSerializer):
    
    address = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "type",
            "email",
            "first_name",
            "last_name",
            "address"
        ]
    
    def get_address(self, obj):
        _id = self.context.get("address_id")
        address = Address.objects.filter(pk=_id).first()
        return AddressSerializer(address).data


class CrmOrderSerializer(DynamicFieldsModelSerializer):
    courier = CrmCourierSerializer()
    customer = serializers.SerializerMethodField()
    timeline = OrderTimelineSerializer()
    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "address",
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
            "timeline",
            "receipt_id",
            "fcm_device",
            "preparing_time",
            "discount_sum",
            "package_amount",
            "package_quantity"
        ]


    def get_customer(self, obj):
        return CrmCustomerSerializer(obj.customer, context={"address_id": obj.address_id}).data

class CrmOrderItemGroupSerializer(DynamicFieldsModelSerializer):
    order = CrmOrderSerializer(
        fields=(
            "id",
            "customer",
            "created_at",
            "status",
            "note",
            "customer_last_name",
            "customer_first_name",
            "courier",
            "customer_phone_number",
        )
    )
    address_order = serializers.CharField(source="order.address.street", read_only=True)
    address_institution = serializers.CharField(source="institution_address_branch", read_only=True)
    institution_branch_name = serializers.CharField(
        source="institution_branch.name", read_only=True
    )
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    operator = CrmUserSerializer(source="order.operator", read_only=True)
    regions = serializers.CharField(source="institution_branch.address.region", read_only=True)

    class Meta:
        model = OrderItemGroup
        fields = [
            "id",
            "order",
            "address_order",
            "address_institution",
            "operator",
            "created_at",
            "updated_at",
            "institution",
            "institution_name",
            "institution_branch",
            "institution_branch_name",
            "products_sum",
            "delivering_sum",
            "total_sum",
            "commission",
            "regions",
        ]


class CrmOrderItemSerializer(DynamicFieldsModelSerializer):
    product = CrmProductSerializer(
        fields=(
            "id",
            "image",
            "name_ru",
            "old_price",
            "price"
        )
    )
    options = serializers.PrimaryKeyRelatedField(
        allow_empty=True, queryset=OptionItem.objects.all(), many=True
    )
    old_product = serializers.SerializerMethodField()
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["options"] = CrmOptionItemShortSerializer(instance.options.all(), many=True).data
        for opt in rep['options']:
            rep['product']['price'] += opt['adding_price']

        return rep
    
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_item_group",
            "product",
            "options",
            "count",
            "total_sum",
            "is_incident",
            "old_product",
        ]

    def get_old_product(self, obj):
        if obj.incident_product:
            order_items = OrderItem.objects.filter(product=obj.incident_product, order_item_group=obj.order_item_group).first()
            if not order_items:
                return None
            serializer = CrmOrderItemSerializer(instance=order_items, 
                fields=(
                    "id",
                    "order_item_group",
                    "product",
                    "options",
                    "count",
                    "total_sum",
                )
            )
            if order_items.options.count() == 0:
                return serializer.data
            options = OptionItemSerializer(order_items.options,
                allow_empty=True, many=True
            ).data
            data = serializer.data
            data['options'] = options
            return data
        return None
   
    # def get_product_flow(self, obj):
    #     chain = []
    #     visited = set()
    #     current_product_id = obj.incident_product_id

    #     while current_product_id and current_product_id not in visited:
    #         visited.add(current_product_id)
    #         print(f"Current product ID: {current_product_id}")
    #         try:
    #             current_item = OrderItem.objects.filter(
    #                 order_item_group=obj.order_item_group,
    #                 product_id=current_product_id
    #             ).first()
    #             print(f"Current item: {current_item}")
    #             chain.append(current_product_id)
    #             current_product_id = current_item.incident_product_id
    #         except OrderItem.DoesNotExist:
    #             break

    #     # return list(reversed(chain))
    #     print(list(reversed(chain)))
    #     return None
    
    
    def validate_count(self, value):
        if value <= 0:
            raise serializers.ValidationError("Значение не может быть меньше единицы")
        return value
    

class CrmOrderItemDetailSerializer(DynamicFieldsModelSerializer):
    product = CrmProductSerializer()
    options = CrmOptionItemSerializer(many=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_item_group",
            "product",
            "count",
            "total_sum",
            "options",
        ]


class CrmOrderItemGroupDetailSerializer(DynamicFieldsModelSerializer):
    items = CrmOrderItemSerializer(many=True)
    order = CrmOrderSerializer(
        fields = (
            "id",
            "courier",
            "created_at",
            "customer",
            "is_paid",
            "note",
            "timeline",
            "payment_method",
            "preparing_time",
            "receipt_id",
            "status",
            "updated_at",
            "package_amount",
            "package_quantity"
        )
    )
    institution_branch_name = serializers.CharField(
        source="institution_branch.name", read_only=True
    )
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    institution_address = serializers.SerializerMethodField()
    products_sum = serializers.IntegerField(source="order.products_sum", read_only=True)
    discount_sum = serializers.IntegerField(source="order.discount_sum", read_only=True)
    total_sum = serializers.IntegerField(source="order.total_sum", read_only=True)
    

    class Meta:
        model = OrderItemGroup
        fields = [
            "id",
            "order",
            "created_at",
            "updated_at",
            "institution",
            "institution_name",
            "institution_branch",
            "institution_address",
            "institution_branch_name",
            "products_sum",
            "delivering_sum",
            "discount_sum",
            "total_sum",
            "commission",
            "items",
        ]
    
    def get_institution_address(self, obj):
        adress = AddressSerializer(obj.institution_branch.address)
        return adress.data
    
class CrmOderUpdateSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = Order
        fields = ("id", "status", "courier", "preparing_time")
        extra_kwargs = {"status": {"required": False}, "courier": {"required": False}}


class CrmOrderItemCreateSerializer(serializers.ModelSerializer):
    options = serializers.PrimaryKeyRelatedField(
        allow_empty=True, queryset=OptionItem.objects.all(), many=True, required=False
    )

    class Meta:
        model = OrderItem
        fields = ["id", "count", "options", "product", "order_item_group", "is_incident", "incident_product"]

    def validate(self, attrs):
        if attrs["product"].institution != attrs["order_item_group"].institution:
            raise serializers.ValidationError("Institution doesnt have this product")
        return attrs


class CrmOrderItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "count", "is_incident"]
