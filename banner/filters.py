from django_filters import FilterSet, filters

from banner.models import Banner


class BannerFilter(FilterSet):
    restaurant = filters.NumberFilter(field_name="restaurant", method="filter_by_restaurant")

    class Meta:
        model = Banner
        fields = ["restaurant"]

    @staticmethod
    def filter_by_restaurant(queryset, name, value):
        if value:
            return queryset.filter(restaurant=value)
        return queryset.filter(restaurant__isnull=True)
