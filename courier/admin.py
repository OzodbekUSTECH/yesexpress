from django.contrib import admin
from .models import Courier, DeliverySettings, InstitutionDeliverySettings, Transaction


@admin.register(DeliverySettings)
class DeliverySettingsAdmin(admin.ModelAdmin):
    list_display = ["__str__", "min_distance", "min_delivery_price", "price_per_km"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    autocomplete_fields = ("user",)


@admin.register(InstitutionDeliverySettings)
class InstitutionDeliverySettingsAdmin(admin.ModelAdmin):
    pass


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["courier", "amount"]
