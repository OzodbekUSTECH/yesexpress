from django.contrib import admin
from .models import Address, Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    fields = ["name_ru", "name_uz", "center", "radius"]

    def get_field_queryset(self, db, db_field, request):
        if db_field.name == "center":
            return Address.objects.select_related("region")
        return super().get_field_queryset(db, db_field, request)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["id", "street", "region", "customer", "institution_branch"]
    list_select_related = ("region",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "region":
            self.fields = ["latitude", "longitude", "region", "street", "institution"]
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
