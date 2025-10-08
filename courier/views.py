import time
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import OuterRef, Exists, Count, Sum, Prefetch
from django.views.generic import TemplateView
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.openapi import Schema, TYPE_STRING, TYPE_OBJECT, TYPE_INTEGER
from drf_yasg.utils import swagger_auto_schema
from order.tasks import delayed_notification_task
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSetMixin
from rest_framework.generics import ListAPIView, RetrieveAPIView

from order.push_notifications.services import send_notification_courier_accept_to_institution
from order.services import calculate_delivering_sum
from order.models import Order, OrderItemGroup
from order.serializers import OrderSerializer
from order.status_controller import update_order_status, assign_order_to_courier
from user.serializers import UserSerializer
from .models import DeliverySettings, Courier, Transaction
from .permissions import IsCourier
from .serializers import (
    DeliveringPriceCalculatorSerializer,
    AvailableOrdersSerializer,
    DeliverySettingsSerializer,
    PhoneNumberSerializer,
    VerifyOTPSerializer,
)


class CourierDemoView(TemplateView):
    template_name = "courier/courier_demo.html"

    def get(self, request, *args, **kwargs):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.send)("telegram-notify", {"type": "test_notify"})
        return super().get(request, *args, **kwargs)


class DeliveryPriceCalculatorView(APIView):
    @swagger_auto_schema(query_serializer=DeliveringPriceCalculatorSerializer())
    def get(self, request):
        serializer = DeliveringPriceCalculatorSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(data=serializer.errors)

        institution = serializer.validated_data["institution"]

        user_address = serializer.validated_data["address"]

        return Response(data={"price": calculate_delivering_sum(institution, user_address)})


class AvailableOrdersViewSet(ViewSetMixin, ListAPIView, RetrieveAPIView):
    item_groups = OrderItemGroup.objects.filter(
        order=OuterRef("pk"),
        institution__delivery_by_own=False,
        institution__branches__is_pickup_available=False,
    )

    queryset = (
        Order.objects.select_related("address", "courier")
        .prefetch_related(
            Prefetch(
                "item_groups",
                queryset=OrderItemGroup.objects.select_related(
                    "institution", "institution__address", "institution_branch", "institution_branch__address"
                )
            )
        )
        .annotate(delivery_by_courier=Exists(item_groups))
        .filter(status="accepted", delivery_by_courier=True, courier__isnull=True)
    )

    serializer_class = AvailableOrdersSerializer
    permission_classes = [IsAuthenticated, IsCourier]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderSerializer
        return AvailableOrdersSerializer


class AssignOrderView(APIView):
    permission_classes = [IsAuthenticated, IsCourier]

    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=404, data={"error": "not found"})

        serializer = AvailableOrdersSerializer(order, context={"request": request})
        return Response(serializer.data)

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=404, data={"error": "not found"})
        if order.status != "accepted":
            return Response(
                data={"result": "error", "error": "the order status is not accepted"}, status=400
            )
        # if order.courier is not None:
        #     return Response(
        #         data= {'status': False, 'message': {'uz': "Kechirasiz, bu buyurtma allaqachon boshqa kuryerga topshirilgan.", "ru": "Извините, этот заказ уже передан другому курьеру.", "en": "Sorry, this order has already been assigned to another courier."}}, status=400
        #     )
        courier = request.user.courier
        is_assign = assign_order_to_courier(order.id, courier)
        if is_assign.get('status'):
            order = is_assign.get('order')

            if order.uuid is not None:
                delayed_notification_task.delay(order.id)
            
            time.sleep(2)
            send_notification_courier_accept_to_institution(order.id)
            
            return Response({"result": "success"})

        return Response(is_assign, status=400)


class GetCourierID(APIView):
    permission_classes = [IsAuthenticated, IsCourier]

    def get(self, request):
        response_data = {
            "courier_id": request.user.courier.id,
            "balance": request.user.courier.balance,
        }

        return Response(data=response_data)

class ChangeStatusView(APIView):
    permission_classes = [IsAuthenticated, IsCourier]

    def post(self, request, pk):
        courier = request.user.courier
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=404, data={"error": "not found"})
        if order.status != "accepted" or order.courier is not None and order.courier != courier:
            return Response(
                data={"result": "error", "error": "the order status is not accepted"}, status=400
            )
        order.timeline.courier_arrived_at = timezone.now()
        order.timeline.save()
        courier.status = Courier.Status.IN_INSTITUTION
        courier.save()

        return Response({"result": "success"})

class GetCourierID(APIView):
    permission_classes = [IsAuthenticated, IsCourier]

    def get(self, request):
        response_data = {
            "courier_id": request.user.courier.id,
            "balance": request.user.courier.balance,
        }

        return Response(data=response_data)


class OrderHistory(APIView):
    """Get order history of courier"""

    permission_classes = [IsAuthenticated, IsCourier]

    @swagger_auto_schema(responses={200: AvailableOrdersSerializer(many=True)})
    def get(self, request):
        courier = request.user.courier
        queryset = (
            Order.objects.filter(courier=courier)
            .annotate(groups_count=Count("item_groups"))
            .filter(groups_count__gt=0)
        )
        serializer = AvailableOrdersSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


class PaymentHistory(APIView):
    """Get order history of courier"""

    permission_classes = [IsAuthenticated, IsCourier]

    @swagger_auto_schema(responses={200: AvailableOrdersSerializer(many=True)})
    def get(self, request):
        courier = request.user.courier
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        orders = Order.objects.prefetch_related("item_groups__items__options") \
            .select_related("customer") \
            .filter(
            courier=self.request.user.courier,
            status__in=[
                "closed"
            ],
        )
        order_agg = orders.aggregate(
            total_delivering_sum=Sum("delivering_sum", default=0),
        )
        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date is required in query params'}, status=400)
        response_data = {}

        response_data['summary'] = {
            "total_earnings": order_agg["total_delivering_sum"],
            "total_fines": 0,
            "grand_total": order_agg["total_delivering_sum"],
        }

        response_data['date_range'] = {
            "start_date": start_date,
            "end_date": end_date
        }

        response_data['payment_items'] = [
            {
                "type": "fixed",
                "title": "Фикса",
                "amount": order_agg["total_delivering_sum"],
                "is_positive": True,
                "details": [
                    {
                        "order_number": f"#{order.id}",
                        "address": order.address.name if order.address else '-',
                        "amount": order.delivering_sum,
                        "is_positive": True
                    }
                    for order in orders
                ]
            },
            {
                "type": "bonus",
                "title": "Бонус",
                "subtitle": "За время доставки",
                "amount": "0",
                "is_positive": True,
                "details": []
            },
            {
                "type": "bonus",
                "title": "Рейтинг",
                "amount": "0",
                "is_positive": True,
                "details": []
            },
            {
                "type": "bonus",
                "title": "Чаевые",
                "amount": "0",
                "is_positive": True,
                "details": []
            },
            {
                "type": "bonus",
                "title": "Штрафы",
                "amount": "0",
                "is_positive": False,
                "details": []
            }
        ]
        return Response(response_data)


#
# class TransactionHistory(APIView):
#     queryset = Transaction.objects.all()
#
#     def get_queryset(self):
#         queryset = super(TransactionHistory, self).get_queryset()
#         return queryset.filter(courier=self.request.user.courier)


class CourierOrdersViewSet(ViewSetMixin, ListAPIView, RetrieveAPIView):
    serializer_class = AvailableOrdersSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    permission_classes = [IsAuthenticated, IsCourier]

    def get_queryset(self):
        return (
            Order.objects.prefetch_related("item_groups__items__options")
            .select_related("customer")
            .annotate(groups_count=Count("item_groups"))
            .filter(
                courier=self.request.user.courier,
                status__in=[
                    "assigned",
                    "pending",
                    "accepted",
                    "ready",
                    "shipped"
                ],
            )
        )


class TakeOrderView(APIView):
    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=404)
        if order.courier == request.user.courier:
            update_order_status(order, "shipped")
            return Response(
                data={
                    "result": "success",
                }
            )
        return Response(status=404)

class CloseOrderView(APIView):
    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=404, data={"error": "not found"})

        order.courier = request.user.courier
        update_order_status(order, "closed")
        return Response(
            data={
                "result": "success",
            }
        )


class DeliverySettingsView(APIView):
    def get(self, request):
        object = DeliverySettings.objects.first()
        serializer = DeliverySettingsSerializer(object)
        return Response(serializer.data)


class ChangeCourierStatus(APIView):
    permission_classes = [IsAuthenticated, IsCourier]

    def post(self, request):
        status = request.data.get("status")
        if status not in Courier.Status.values:
            return Response({"status": "error", "detail": "incorrect status"}, status=400)

        courier: Courier = request.user.courier
        courier.status = status
        courier.save()
        return Response({"status": "success"})

class Topup(APIView):
    permission_classes = [IsAuthenticated, IsCourier]

    def post(self, request):
        amount = request.data.get("amount")
        courier: Courier = request.user.courier

        transaction = Transaction.objects.create(courier=courier, amount=amount, type='in')


        if not transaction:
            return Response({"status": "error", "detail": "incorrect status"}, status=400)
        
        return Response({"status": "success"})


class GetVerificationCodeAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        request_body=Schema(
            properties={"phone_number": Schema(type=TYPE_STRING)},
            type=TYPE_OBJECT,
        )
    )
    def post(self, request, *args, **kwargs):
        serializer = PhoneNumberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"status": "success"})


class VerifyAPIView(APIView):
    # better to rename View's name, or write description
    # verify of what ? is this method
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        request_body=Schema(
            properties={
                "phone_number": Schema(type=TYPE_STRING),
                "sms_code": Schema(type=TYPE_INTEGER),
            },
            type=TYPE_OBJECT,
            required=["phone_number", "sms_code"],
        )
    )
    def post(self, request, *args, **kwargs):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response(UserSerializer(user).data)
