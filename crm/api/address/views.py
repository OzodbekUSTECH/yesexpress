from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from address.models import Region, Address
from address.swagger import MULTIPOINT_RESPONSE_BODY, MULTIPOINT_REQUEST_BODY
from base.api_views import MultiSerializerViewSetMixin, DynamicPagination
from crm.api.address.serializers import CrmRegionSerializer, CrmInstitutionAddressSerializer
from .filters import InstitutionAddressFilter
from .permissions import AddressPermission


@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        request_body=MULTIPOINT_REQUEST_BODY, responses=MULTIPOINT_RESPONSE_BODY
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        request_body=MULTIPOINT_REQUEST_BODY, responses=MULTIPOINT_RESPONSE_BODY
    ),
)
@method_decorator(name="list", decorator=swagger_auto_schema(responses=MULTIPOINT_RESPONSE_BODY))
@method_decorator(
    name="retrieve", decorator=swagger_auto_schema(responses=MULTIPOINT_RESPONSE_BODY)
)
class RegionViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Region.objects.all()
    serializer_action_classes = {
        "list": CrmRegionSerializer,
        "retrieve": CrmRegionSerializer,
        "create": CrmRegionSerializer,
        "partial_update": CrmRegionSerializer,
    }
    permission_classes = [IsAuthenticated, AddressPermission]
    pagination_class = DynamicPagination


class InstitutionAddressViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Address.objects.filter(institution__isnull=False)
    serializer_action_classes = {
        "list": CrmInstitutionAddressSerializer,
        "retrieve": CrmInstitutionAddressSerializer,
        "create": CrmInstitutionAddressSerializer,
        "partial_update": CrmInstitutionAddressSerializer,
    }
    permission_classes = [IsAuthenticated, AddressPermission]
    pagination_class = DynamicPagination
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]
    filterset_class = InstitutionAddressFilter
    search_fields = ["name", "street", "reference_point"]
