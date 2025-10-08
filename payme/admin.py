from django.contrib import admin
from .models import PaymePayment

@admin.register(PaymePayment)
class PaymePaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "receipt_id", "total_sum", "order", "card", "status", "created_at"
    )
    list_filter = ("status", "created_at")
    search_fields = ("receipt_id", "order__id", "card__number")
    readonly_fields = (
        "create_receipt_request", "create_receipt_response",
        "pay_receipt_request", "pay_receipt_response",
        "confirm_request", "confirm_response",
        "cancel_request", "cancel_response",
    )
    ordering = ("-created_at",)
    
    @admin.display(description="Order")
    def order_display(self, obj):
        return f"Заказ №{obj.order.id}"
