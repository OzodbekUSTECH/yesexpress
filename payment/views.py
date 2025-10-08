from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from base.api_views import MultiSerializerViewSetMixin, CustomPagination
from payment.models import Payment
from payment.serializers import PaymentSerializer


class PaymentViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Payment.objects.get_available().prefetch_related("ofd_receipts")
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
    ]
    filterset_fields = ["order"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(order__customer=self.request.user)
        return qs
