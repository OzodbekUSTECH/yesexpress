from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from base.api_views import DynamicPagination, MultiSerializerViewSetMixin
from courier.models import Courier, DeliverySettings
from courier.services import CourierFilter, get_delivery_settings
from user.models import User
from .serializers import (
    CrmCourierSerializer,
    CrmCourierUpdateSerializer,
    CrmDeliverySettingsSerializer,
)
from .permissions import CourierPermission


class CourierViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Courier.objects.filter(is_deleted=False)
    serializer_action_classes = {
        "list": CrmCourierSerializer,
        "retrieve": CrmCourierSerializer,
        "create": CrmCourierSerializer,
        "partial_update": CrmCourierUpdateSerializer,
    }
    permission_classes = [IsAuthenticated, CourierPermission]
    pagination_class = DynamicPagination
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter
    ]

    # filterset_fields = ["status", "transport"]
    filterset_class = CourierFilter
    search_fields = ["user__phone_number"]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.data.get('user', {}).get('phone_number') == instance.user.phone_number:
            request.data.get('user', {}).pop('phone_number')
        
        return super().partial_update(request, *args, **kwargs)
        
            
        
    def destroy(self, request, *args, **kwargs):
        courier: Courier = self.get_object()
        if courier.status == "delivering":
            return Response({"message": "Курьер доставляет заказ"}, status=400)
        courier.is_deleted = True
        courier.save()
        return Response(status=204)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        total_couriers = Courier.objects.filter(is_deleted=False).count()
        active_couriers = Courier.objects.filter(
            is_deleted=False, status=Courier.Status.FREE
        ).count()
        inactive_couries = Courier.objects.filter(
            is_deleted=False, status=Courier.Status.INACTIVE
        ).count()

        return Response(
            {
                "total_couriers": total_couriers,
                "active_couriers": active_couriers,
                "inactive_couries": inactive_couries,
            }
        )


class DeliverySettingsViewSet(ModelViewSet):
    queryset = DeliverySettings.objects.all()
    serializer_class = CrmDeliverySettingsSerializer
    permission_classes = [IsAuthenticated, CourierPermission]

    def get_object(self):
        return get_delivery_settings()
