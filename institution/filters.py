from django_filters import FilterSet, filters
from django.db.models import Q
from institution.models import Institution


class InstitutionFilterSet(FilterSet):
    region = filters.CharFilter(lookup_expr="icontains")
    category_id = filters.NumberFilter(method="filter_categories")
    search = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Institution
        fields = ["search", "region", "category_id", 'is_popular']

    @staticmethod
    def filter_categories(queryset, name, value):
      
        return queryset.filter(Q(secondary_categories__in=value))
        
        # return queryset
