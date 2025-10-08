from .models import Courier, DeliverySettings
from django_filters import rest_framework as filters
from django.db.models import Q

def get_delivery_settings():
    return None
    return DeliverySettings.objects.first()

class CourierFilter(filters.FilterSet):
    phone_number = filters.CharFilter(field_name='user__phone_number', lookup_expr='icontains')
    name = filters.CharFilter(method='filter_name')
    region = filters.CharFilter(method='filter_region')

    class Meta:
        model = Courier
        fields = ['id', 'status', 'transport', 'registration_number', 'thermal_bag_number', 'region', 'phone_number', 'name']
    
    def filter_name(self, queryset, name, value):
        return queryset.filter(
            Q(user__first_name__icontains=value) | Q(user__last_name__icontains=value)
        )
    
    def filter_region(self, queryset, name, value):
        return queryset.filter(Q(user__address__region__pk=value))