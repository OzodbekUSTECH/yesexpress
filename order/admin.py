from django.contrib import admin
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import TokenProxy

from address.models import Address
from courier.models import Courier
from .models import Order, OrderItem, OrderItemGroup, OrderStatusTimeline

admin.site.unregister(TokenProxy)
admin.site.unregister(Group)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ["created_at", "fcm_device"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("customer")

    def get_field_queryset(self, db, db_field, request):
        queryset = super().get_field_queryset(db, db_field, request)
        if db_field.name == "address":
            return Address.objects.select_related("region")
        elif db_field.name == "courier":
            return Courier.objects.select_related("user")
        return queryset


@admin.register(OrderItemGroup)
class OrderItemGroupAdmin(admin.ModelAdmin):
    
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order")

@admin.register(OrderStatusTimeline)
class OrderStatusTimelineAdmin(admin.ModelAdmin):
    list_display = [
        "preparing_start_at",
        "preparing_completed_at",
        "preparing_lates",
        "courier_assign_at",
        "courier_take_it_at",
        "courier_lates",
        "delivered_at",
        "order"
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = "product", "count", "total_sum", "get_order_id"

    @admin.display(ordering="order_item_group__order", description="№ заказа")
    def get_order_id(self, obj):
        return obj.order_item_group.order_id
