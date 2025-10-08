from django_filters import rest_framework as filters

from courier.models import Courier
from order.models import Order, OrderItemGroup


class CrmOrderFilter(filters.FilterSet):
    created_date_after = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_date_before = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Order
        fields = ["status"]


class OrderItemGroupFilter(filters.FilterSet):
    id = filters.NumberFilter(field_name="order__id")
    created_date_after = filters.DateTimeFilter(field_name="order__created_at", lookup_expr="gte")
    created_date_before = filters.DateTimeFilter(field_name="order__created_at", lookup_expr="lte")
    no_courier = filters.BooleanFilter(method='filter_no_courier')
    lates = filters.BooleanFilter(method='filter_lates')
    status = filters.MultipleChoiceFilter(choices=Order.STATUSES, field_name="order__status")
    courier = filters.ModelChoiceFilter(queryset=Courier.objects.all(), field_name="order__courier")
    regions = filters.CharFilter(
        field_name="institution_branch__address__region__name", lookup_expr="icontains"
    )
    customer_phone_number = filters.CharFilter(
        field_name="order__customer__phone_number", lookup_expr="icontains"
    )

    class Meta:
        model = OrderItemGroup
        fields = ["id","status", "institution", "regions", "customer_phone_number", "no_courier", "lates", "courier", "created_date_after", "created_date_before"]

    def filter_no_courier(self, queryset, name, value):
        if value is True:
            return queryset.filter(order__courier__isnull=True)
        elif value is False:
            return queryset.filter(order__courier__isnull=False)
        return queryset
    
    def filter_lates(self, queryset, name, value):
        if value is True:
            return queryset.filter(order__courier__isnull=True)
        elif value is False:
            return queryset.filter(order__courier__isnull=False)
        return queryset