from django.contrib import admin

from .models import Product, ProductOption, ProductCategory, OptionItem


@admin.register(ProductCategory)
class CategoryAdmin(admin.ModelAdmin):
    fields = ["name_ru", "name_uz", "name_en", "position", "institution", "is_active"]


class OptionItemInline(admin.TabularInline):
    model = OptionItem
    fields = ["title_ru", "title_uz", "title_en", "option", "adding_price", "is_default"]


@admin.register(ProductOption)
class ProductOptionAdmin(admin.ModelAdmin):
    fields = ["title_ru", "title_uz", "title_en", "is_required", "product"]
    inlines = [OptionItemInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name_ru", "institution", "price"]

    fields = [
        "name_ru",
        "name_uz",
        "name_en",
        "description_ru",
        "description_uz",
        "image",
        "status",
        "price",
        "category",
        "institution",
        "spic_id",
        "package_code",
    ]
