import django_filters
from address.models import Address


class InstitutionAddressFilter(django_filters.FilterSet):
    region = django_filters.NumberFilter(field_name="region", lookup_expr="exact")
    institution = django_filters.NumberFilter(field_name="institution", lookup_expr="exact")

    class Meta:
        model = Address
        fields = ["region", "institution"]
