from django_filters.rest_framework import FilterSet, filters

from order.models import Order


class OrderFilter(FilterSet):
    institution_branch = filters.NumberFilter(
        field_name="institution_branch",
        method="filter_by_restaurant"
    )
    start_date = filters.DateFilter(
        field_name="start_date",
        method="filter_by_start_date"
    )
    end_date = filters.DateFilter(
        field_name="end_date",
        method="filter_by_end_date"
    )
    courier = filters.NumberFilter(
        field_name="courier",
    )

    class Meta:
        model = Order
        fields = (
            "institution_branch",
            'status',
            'start_date',
            'end_date',
            'courier'
        )

    @staticmethod
    def filter_by_restaurant(queryset, name, value):
        if value:
            return queryset.filter(item_groups__institution_branch=value)
        return queryset

    @staticmethod
    def filter_by_start_date(queryset, name, value):
        if value:
            return queryset.filter(created_at__gte=value)
        return queryset

    @staticmethod
    def filter_by_end_date(queryset, name, value):
        if value:
            return queryset.filter(created_at__lte=value)
        return queryset

    @staticmethod
    def filter_by_courier(queryset, name, value):
        if value:
            return queryset.filter(courier_id=value)
        return queryset