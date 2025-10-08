from rest_framework.viewsets import ModelViewSet

from base.api_views import MultiSerializerViewSetMixin
from crm.api.promo_code.serializers import CrmPromoCodeSerializer
from order.promo_codes.models import PromoCode

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as http_status

class PromoCodeView(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = PromoCode.objects.filter(status='active').all()
    serializer_class = CrmPromoCodeSerializer

    def partial_update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        users = serializer.validated_data.pop('users', None)

        self.perform_update(serializer)

        if users is not None:
            instance.users.set(users)

        return Response(serializer.data, status=http_status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = "deleted"
        instance.is_active = False
        instance.save(update_fields=["status", "is_active"])
        return Response({"detail": "Promo code status set to deleted and inactivated."}, status=http_status.HTTP_204_NO_CONTENT)