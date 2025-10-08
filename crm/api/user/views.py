from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.openapi import Schema, TYPE_STRING, TYPE_OBJECT
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db.models import Count, Q, Sum
from rest_framework.filters import OrderingFilter
from rest_framework import status
from base.api_views import MultiSerializerViewSetMixin, CustomPagination
from crm.api.user.serializers import (
    CustomTokenObtainSerializer,
    CrmUserSerializer,
    CrmUserUpdateSerializer,
)

from rest_framework.decorators import action
from user.models import CustomFCMDevice
from user.serializers import CustomFCMDeviceSerializer
User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    @swagger_auto_schema(
        request=CustomTokenObtainSerializer,
        responses={
            200: CustomTokenObtainSerializer,
            401: Schema(
                properties={
                    "detail": Schema("User does not exists", type=TYPE_STRING),
                },
                type=TYPE_OBJECT,
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ActiveUserViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_action_classes = {
        "retrieve": CrmUserSerializer,
        "partial_update": CrmUserUpdateSerializer,
    }
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(instance=user)
        return Response(serializer.data)

    def remove_avatar(self, request, *args, **kwargs):
        user = request.user
        user.avatar = None
        user.save()
        serializer = CrmUserSerializer(instance=user)
        return Response(serializer.data)


class WorkerViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = User.objects.filter(type__in=User.get_worker_types())
    serializer_action_classes = {
        "list": CrmUserSerializer,
        "retrieve": CrmUserSerializer,
        "create": CrmUserSerializer,
        "partial_update": CrmUserUpdateSerializer,
    }
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["type"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        return Response({"detail": "Worker marked as inactive."}, status=status.HTTP_204_NO_CONTENT)

class ClientsViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = User.objects.filter(is_superuser=False, type=None).prefetch_related("used_promo_codes").annotate(total_orders=Count("order"), closed_orders=Count("order", filter=Q(order__status="closed")), rejected_orders=Count("order", filter=Q(order__status="rejected")), total_sum=Sum("order__total_sum"))
    serializer_action_classes = {
        "list": CrmUserSerializer,
        "retrieve": CrmUserSerializer,
        "create": CrmUserSerializer,
        "partial_update": CrmUserUpdateSerializer,
    }
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["total_orders", "closed_orders", "rejected_orders", "id", "date_joined", "total_sum"]
    filterset_fields = ["is_active"]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        phone_number = self.request.query_params.get("phone_number")

        if phone_number:
            clean_number = phone_number.replace('+', '')
            queryset = queryset.filter(
                Q(phone_number__icontains=clean_number) |
                Q(phone_number__icontains='+' + clean_number)
            )
            # queryset = queryset.filter(phone_number__icontains=phone_number)

        return queryset
    
    @action(detail=False, methods=["post"], url_path="device")
    def device(self, request):
        user = request.user
        app_name = request.data.get("app_name")

        # Eski device-ni topish va o'chirish
        if app_name:
            existing_device = CustomFCMDevice.objects.filter(user=user, app_name=app_name).first()
            if existing_device:
                existing_device.delete()

        # Yangi device-ni saqlash
        serializer = CustomFCMDeviceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from rest_framework.views import APIView
class RegisterDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = CustomFCMDeviceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            register_id = request.data.get("registration_id")
            app_name = request.data.get('app_name')
            type = request.data.get('type')
            device = CustomFCMDevice.objects.filter(user=user, registration_id=register_id, app_name=app_name, type=type).first()
            if device:
                device.delete()

            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": f"User not found, {e}", "error_code": "-2"}, status.HTTP_400_BAD_REQUEST)