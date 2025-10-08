from django.contrib.gis.geos import Point
from easy_thumbnails.templatetags.thumbnail import thumbnail_url
from rest_framework import serializers

from institution.models import InstitutionBranch
from .models import Product, ProductCategory, ProductOption, OptionItem, ProductToBranch


class ThumbnailSerializer(serializers.ImageField):
    def __init__(self, alias, **kwargs):
        super().__init__(**kwargs)
        self.alias = alias
        self.read_only = True

    def to_representation(self, value):
        request = self.context.get("request")
        url = thumbnail_url(value, self.alias)
        if request:
            url = request.build_absolute_uri(url)
        return url


class OptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionItem
        fields = ["id", "title_ru", "title_uz", "title_en", "adding_price", "is_default"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['title_uz'] = data['title_uz'] or data['title_ru']
        data['title_en'] = data['title_en'] or data['title_ru']
        return data


class OptionSerializer(serializers.ModelSerializer):
    items = OptionItemSerializer(many=True)

    class Meta:
        model = ProductOption
        fields = ["id", "title_ru", "title_uz", "title_en", "is_required", "items"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['title_uz'] = data['title_uz'] or data['title_ru']
        data['title_en'] = data['title_en'] or data['title_ru']
        return data


class ProductListSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="product-detail")
    image = ThumbnailSerializer("small")
    price_display = serializers.SerializerMethodField()
    old_price = serializers.SerializerMethodField()
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "url",
            "name_ru",
            "name_uz",
            "name_en",
            "image",
            "price",
            "old_price",
            "status",
            "institution",
            "price_display",
            "description",
            "options",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['name_uz'] = data['name_uz'] or data['name_ru']
        data['name_en'] = data['name_en'] or data['name_ru']
        return data

    def get_old_price(self, obj):
        return obj.old_price if obj.old_price is not None and obj.old_price > 0 else None

    def get_price_display(self, obj):
        options_sum = 0
        for option in obj.options.all():
            if option.is_required:
                min_ = min([item.adding_price for item in option.items.all()])
                options_sum += min_

        return obj.price + options_sum


class ProductListBranchSerializer(ProductListSerializer):
    def to_representation(self, instance):

        lat = self.context.get("lat")
        long = self.context.get("long")

        if lat and long:
            institution_branches = InstitutionBranch.objects.filter(region_branch__polygon__contains=Point((float(lat),float(long)))).first()
            
            product_to_institution_branches, created = ProductToBranch.objects.get_or_create(
                product=instance,
                institution_branches=institution_branches,
                defaults={
                    'is_available': True,
                }
            )
            setattr(instance, "is_available", product_to_institution_branches.is_available)
        return super().to_representation(instance)


class CategoryListSerializer(serializers.ModelSerializer):
    product_set = serializers.SerializerMethodField()
    class Meta:
        model = ProductCategory
        fields = ["id", "name_ru", "name_uz", "name_en", "product_set", "is_active"]

    def get_product_set(self, obj):
        products = obj.product_set.filter(status='active')
        serializer = ProductListBranchSerializer(
            products,
            many=True,
            read_only=True,
            context=self.context
        )
        return serializer.data
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['name_uz'] = data.get('name_uz') or data.get('name_ru', '-')
        data['name_en'] = data.get('name_en') or data.get('name_ru', '-')
        return data
        
class ProductDetailSerializer(ProductListSerializer):
    options = OptionSerializer(many=True, read_only=True)
    is_liked = serializers.BooleanField(read_only=True)
    image = ThumbnailSerializer("big")

    class Meta(ProductListSerializer.Meta):
        fields = [
            "id",
            "name_ru",
            "name_uz",
            "name_en",
            "image",
            "price",
            "description_ru",
            "description_uz",
            "description_en",
            "options",
            "is_liked",
            "institution",
            "price_display",
            "is_available"
        ]
