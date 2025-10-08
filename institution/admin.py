from django.contrib import admin
from .models import InstitutionCategory, Institution, InstitutionBranch
from address.models import Address


class AddressInline(admin.StackedInline):
    min_num = 1
    max_num = 1
    model = Address
    fields = ["region", "street", "reference_point"]


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Информация",
            {
                "fields": (
                    "name",
                    "description_ru",
                    "description_uz",
                    "description_en",
                    "phone_number",
                    "type",
                    "category",
                    "secondary_categories",
                    "image",
                    "logo",
                    "balance",
                    "position",
                    "is_deleted",
                    "is_active",
                )
            },
        ),
        ("Заказ", {"fields": ("delivery_by_own", "tax_percentage_ordinary", "free_delivery")}),
        (
            "График работы",
            {
                "fields": (
                    "start_time",
                    "end_time",
                )
            },
        ),
        (
            "Администрация",
            {
                "fields": (
                    "owner",
                    "admin",
                )
            },
        ),
    )

    inlines = [AddressInline]


@admin.register(InstitutionBranch)
class InstitutionBranchAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "institution")


@admin.register(InstitutionCategory)
class InstitutionCategoryAdmin(admin.ModelAdmin):
    fields = ("icon", "title_ru", "title_uz", "title_en", "position")
    list_display = ("title_ru",)
