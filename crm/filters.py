import django_filters

from order.models import OrderItem, OrderItemGroup


class InstitutionOrderFilter(django_filters.FilterSet):
    date_range = django_filters.DateFromToRangeFilter(field_name="order__created_at")

    class Meta:
        model = OrderItem
        fields = ("date_range",)


class OrderFilter(django_filters.FilterSet):
    f_created_at = django_filters.DateFromToRangeFilter(field_name="order__created_at")
    status = django_filters.CharFilter(field_name="order__status")
    payment_method = django_filters.CharFilter(field_name="order__payment_method")

    class Meta:
        model = OrderItemGroup
        fields = ["institution", "f_created_at", "status", "payment_method"]
