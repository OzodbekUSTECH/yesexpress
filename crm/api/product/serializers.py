from drf_extra_fields.fields import Base64ImageField
from institution.models import InstitutionBranch
from product.serializers import OptionItemSerializer
from rest_framework import serializers

from base.serializer import DynamicFieldsModelSerializer, MultiLanguageFieldSerializerMixin
from product.models import Product, ProductCategory, OptionItem, ProductOption, ProductToBranch

class UnavailableProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "status"]

class CrmProductCategorySerializer(DynamicFieldsModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    unavailable = serializers.SerializerMethodField()
    class Meta:
        model = ProductCategory
        fields = [
            "id",
            "name_ru",
            "name_uz",
            "name_en",
            "position",
            "institution",
            "institution_name",
            "is_active",
            "unavailable"
        ]
    
    def get_unavailable(self, obj):
        branch_id = self.context.get("branches_id")
        if not branch_id:
            return False
        
        product_ids = obj.product_set.values_list("id", flat=True)
        if isinstance(branch_id, list):
            unavailable_product_ids = ProductToBranch.objects.filter(
                institution_branches__in=branch_id,
                product_id__in=product_ids,
                is_available=False
            ).values_list("product_id", flat=True).distinct()
        else:
            unavailable_product_ids = ProductToBranch.objects.filter(
                institution_branches=branch_id,
                product_id__in=product_ids,
                is_available=False
            ).values_list("product_id", flat=True).distinct()

        products = obj.product_set.filter(id__in=unavailable_product_ids)
        if products:
            return True
        return False
        # return UnavailableProductSerializer(products, many=True).data


class CrmOptionItemSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = OptionItem
        fields = [
            "id",
            "title_ru",
            "title_uz",
            "title_en",
            "adding_price",
            "is_default",
            "is_deleted",
        ]

class CrmOptionItemShortSerializer(MultiLanguageFieldSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = OptionItem
        fields = [
            "title_ru",
            "adding_price"
        ]


class CrmProductOptionSerializer(DynamicFieldsModelSerializer):
    items = CrmOptionItemSerializer(many=True)

    class Meta:
        model = ProductOption
        fields = ["id", "product", "title_ru", "title_uz", "title_en", "is_required", "items"]


class CrmProductSerializer(MultiLanguageFieldSerializerMixin, DynamicFieldsModelSerializer):
    category_obj = CrmProductCategorySerializer(source="category", read_only=True)
    status = serializers.CharField(default="active")
    unavailable = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "short_description",
            "price",
            "old_price",
            "image",
            "status",
            "category",
            "category_obj",
            "institution",
            "is_available",
            "unavailable"
        ]
        extra_kwargs = {"image": {"read_only": True}}

    def get_unavailable(self, obj):
        branch_id = self.context.get("branches_id")
        if not branch_id:
            return False
        if isinstance(branch_id, list):
            unavailable_product_ids = ProductToBranch.objects.filter(
                institution_branches__in=branch_id,
                product_id=obj.id,
                is_available=False
            ).values_list("product_id", flat=True).distinct()
        else:
            unavailable_product_ids = ProductToBranch.objects.filter(
                institution_branches=branch_id,
                product_id=obj.id,
                is_available=False
            ).values_list("product_id", flat=True).distinct()

        if unavailable_product_ids:
            return True
        return False
class CrmProductToBranchSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='institution_branches.name')

    class Meta:
        model = ProductToBranch
        fields = [
            'branch_name',
            'institution_branches',
            'is_available',
        ]



class CrmProductDetailSerializer(CrmProductSerializer):
    options = CrmProductOptionSerializer(many=True, read_only=True)
    # branches = CrmProductToBranchSerializer(many=True, read_only=True)
    vat = serializers.SerializerMethodField()
    branches = serializers.SerializerMethodField()

    class Meta(CrmProductSerializer.Meta):
        model = Product
        fields = CrmProductSerializer.Meta.fields + [
            "external_id",
            "description",
            "spic_id",
            "package_code",
            "vat",
            "options",
            "commission",
            "branches"
        ]
    
    def get_vat(self, obj):
        return True if obj.vat == 12 else False
   
    def get_branches(self, obj):
        return [
            {
                "id": pb.institution_branches.id,
                "name": pb.institution_branches.name,
                "status": pb.is_available,
                "is_available": pb.is_available,
                "institution_branches": pb.institution_branches.id,
            }
            for pb in obj.branches.all()
        ]

class CrmProductCreateSerializer(MultiLanguageFieldSerializerMixin, serializers.ModelSerializer):
    image_upload = Base64ImageField(source="image", required=False, write_only=True)
    vat = serializers.BooleanField(write_only=True, required=False, default=False)
    
    def create(self, validated_data):
        
        # vat_bool = validated_data.pop("vat", False)
        # validated_data["vat"] = 12 if vat_bool else 0
        
        product = super().create(validated_data)
        branches = product.institution.branches.all()
        product_to_branch = []
        for branch in branches:
            product_to_branch.append(ProductToBranch(
                product=product,
                institution_branches=branch,
                is_available=True
            ))
        ProductToBranch.objects.bulk_create(product_to_branch)
        return product
    
    def update(self, instance, validated_data):
        vat_bool = validated_data.pop("vat", None)
        if vat_bool is not None:
            instance.vat = 12 if vat_bool else 0

        return super().update(instance, validated_data)
    
    class Meta:
        model = Product
        fields = [
            "id",
            "external_id",
            "name",
            "short_description",
            "description",
            "commission",
            "price",
            "old_price",
            "image_upload",
            "status",
            "category",
            "institution",
            "spic_id",
            "package_code",
            "vat",
        ]
        extra_kwargs = {
            "image": {"read_only": True},
            "external_id": {"required": False},
            "old_price": {"required": False},
            "vat": {"required": False},
        }


class CrmProductOptionCreateSerializer(DynamicFieldsModelSerializer):
    items = CrmOptionItemSerializer(many=True)

    class Meta:
        model = ProductOption
        fields = [
            "id",
            "product",
            "title_ru",
            "title_uz",
            "title_en",
            "is_required",
            "items",
        ]

    def create(self, validated_data):
        items = validated_data.pop("items", None)
        instance = ProductOption.objects.create(**validated_data)
        if items:
            for item in items:
                OptionItem.objects.create(**item, option=instance)
        return instance


class CrmProductOptionUpdateSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = ProductOption
        fields = [
            "id",
            "product",
            "title_ru",
            "title_uz",
            "title_en",
            "is_required",
        ]


class CrmOptionItemUpdateSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = OptionItem
        fields = [
            "id",
            "title_ru",
            "title_uz",
            "title_en",
            "option",
            "adding_price",
            "is_default",
            "is_deleted",
        ]
