import calendar
from datetime import timedelta, datetime

from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum, F, Avg
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend

from base.api_views import MultiSerializerViewSetMixin, CustomPagination
from institution.models import InstitutionBranch
from order.feedback.models import InstitutionFeedback
from order.feedback.serializers import InstitutionFeedbackSerializer
from order.models import Order, ORDER_STATUS
from order.utils import notify_courier, notify_institution, notify_operator
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from order.serializers import OrderRestaurantSerializer, OrderSerializer
from order.status_controller import update_order_status
from .filters import OrderFilter
from .serializers import (
    RestaurantOrderSerializer,
    OrderActionModelSerializer, RestaurantInstitutionListSerializer, RestaurantUserSerializer,
    RestaurantUserUpdateSerializer, RestaurantUserCreateSerializer,
)

User = get_user_model()

class RestaurantInstitutionViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RestaurantInstitutionListSerializer

    def get_queryset(self):
        user = self.request.user
        branches = InstitutionBranch.objects.filter(
            Q(
                Q(institution__owner=user) | Q(institution__admin=user) | Q(workers__worker=user)
            )
        ).distinct()
        return branches


class RestaurantWorkerViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = User.objects.filter(type='institution_worker')
    serializer_action_classes = {
        "list": RestaurantUserSerializer,
        "retrieve": RestaurantUserSerializer,
        "create": RestaurantUserCreateSerializer,
        "partial_update": RestaurantUserUpdateSerializer,
    }
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        return super().get_queryset().filter(
            Q(worker_branch__institution_branch__institution__owner=self.request.user) |
            Q(worker_branch__institution_branch__institution__admin=self.request.user)
        ).order_by("id")


class OptionalPagination(PageNumberPagination):
    page_size = 15
    page_query_param = 'page'
    page_size_query_param = 'per_page'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if self.page_query_param in request.query_params:
            return super().paginate_queryset(queryset, request, view)
        return None

    def get_paginated_response(self, data):
        return Response({
            'total': self.page.paginator.count,
            'page': self.page.number,
            'pages': self.page.paginator.num_pages,
            'per_page': self.get_page_size(self.request),
            'results': data
        })
    
class OrderActionsViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderRestaurantSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter
    pagination_class = OptionalPagination
    
    def get_queryset(self):
        inst = self.request.user.get_institution()
        queryset = Order.objects.select_related('address', 'customer', 'courier', 'operator', 'address__region').prefetch_related().filter().distinct()
        if inst:
            if self.request.user.type == 'institution_worker':
                queryset = queryset.filter(item_groups__institution_branch=inst)
            else:
                queryset = queryset.filter(item_groups__institution=inst)
        
        promo_code = self.request.query_params.get("promo_code")
        if promo_code == "true":
            queryset = queryset.filter(discount_sum__gt=0)  # yoki promo_code__isnull=False
        elif promo_code == "false":
            queryset = queryset.filter(Q(discount_sum=0) | Q(discount_sum__isnull=True))
        
        history_queryset = queryset.filter(
            status__in=[
                ORDER_STATUS.READY.value,
                ORDER_STATUS.COOKING.value,
                ORDER_STATUS.SHIPPED.value,
                ORDER_STATUS.CLOSED.value,
                ORDER_STATUS.REJECTED.value,
                ORDER_STATUS.INCIDENT.value,
                ORDER_STATUS.CREATED,
                ORDER_STATUS.PENDING,
            ]
        )

        active_orders_queryset = queryset.filter(
            status__in=[ORDER_STATUS.CREATED, ORDER_STATUS.COOKING.value, ORDER_STATUS.INCIDENT, ORDER_STATUS.PENDING, ORDER_STATUS.ACCEPTED.value, ORDER_STATUS.READY]
        )
        action_querysets = {
            "active": active_orders_queryset,
            "history": history_queryset,
            "retrieve": queryset,
            "accept": queryset,
            "cooking": queryset,
            "order_stats": queryset,
            "cancel": queryset.filter(
                status__in=[ORDER_STATUS.PENDING.value, ORDER_STATUS.INCIDENT.value, ORDER_STATUS.ACCEPTED.value]
            ),
            "ready": queryset,
        }
        return action_querysets.get(self.action, queryset)

    def get_serializer_class(self) -> OrderActionModelSerializer:  # type hint working
        return super().get_serializer_class()

    def get_object(self) -> Order:
        return super().get_object()

    @action(methods=["post"], detail=True)
    def accept(self, request: Request, pk):
        order: Order = self.get_object()
        if order.status not in [ORDER_STATUS.CREATED, ORDER_STATUS.PENDING]:
            return Response({"message": f'Эту операцию нельзя выполнить для данного заказа {order.id}. Текущий статус заказа: {order.get_status_display()}.'}, status=400)
        preparing_time = request.data.get("preparing_time", 0)
        order.preparing_time = preparing_time
        update_order_status(order, "accepted", preparing_time)
        notify_courier(order)
        notify_operator(order)
        notify_institution(order)
        return Response({"message": f"Заказ {order.id} принят и перемещен в статус 'accepted'."})
    
    @action(methods=["post"], detail=True)
    def process(self, request: Request, pk):
        order: Order = self.get_object()
        is_process = request.data.get("is_process")
        if is_process:
            order.is_process = is_process
        else:
            order.is_process = False
            order.preparing_time = request.data.get("preparing_time", 0)
            order.status = ORDER_STATUS.INCIDENT
        order.save()
        notify_courier(order)
        notify_operator(order)
        notify_institution(order)
        return Response({"message": f'Заказ {order.id} в процессе обработки.'})

    @action(methods=["post"], detail=True)
    def change_preparing_time(self, request: Request, pk):
        order = Order.objects.get(pk=pk)
        preparing_time = request.POST.get("preparing_time")
        if order.status in ['ready', 'rejected', 'closed']:
            return Response({"message": f'Эту операцию нельзя выполнить для данного заказа {order.id}. Текущий статус заказа: {order.get_status_display()}.'})
        order.preparing_time = preparing_time
        order.save()
        notify_courier(order)
        notify_operator(order)
        notify_institution(order)
        return Response({"message": f'Заказ {order.id} принят и перемещен в статус "accepted".'})

    @action(methods=["post"], detail=True)
    def cancel(self, request: Request, pk):
        order = Order.objects.get(pk=pk)
        update_order_status(order, "rejected")
        notify_courier(order)
        notify_operator(order)
        notify_institution(order)
        return Response({"message": f'Заказ {order.id} отменен и перемещен в статус "closed"'})
    
    @action(methods=["post"], detail=True)
    def cooking(self, request: Request, pk):
        order = Order.objects.get(pk=pk)
        if order.status == ORDER_STATUS.ACCEPTED:
            update_order_status(order, "cooking")
            return Response({"message": f'Заказ {order.id} приготовится и перемещен в статус "cooking"'})
        if order.status == ORDER_STATUS.COOKING:
            return Response({"message": f'Заказ {order.id} уже в статусе "cooking"'})
        return Response({"message": f'Заказ {order.id} еще не принят рестораном или курьер не назначен.'})

    @action(methods=["post"], detail=True)
    def ready(self, request, pk):
        order = self.get_object()
        if order.status in [ORDER_STATUS.ACCEPTED, ORDER_STATUS.COOKING]:
            update_order_status(order, "ready")
            notify_courier(order)
            notify_operator(order)
            notify_institution(order)
            return Response({"message": f'Заказ {order.id} готов и перемещен в статус "ready". '})
        return Response({"message": f'Заказ {order.id} не принят или не приготовлен.'})

    @action(methods=["get"], detail=False)
    def active(self, request):
        return Response(RestaurantOrderSerializer(self.get_queryset(), many=True).data)
    
    @action(methods=["get"], detail=False)
    def history(self, request):
        queryset = self.get_queryset().filter(
            status__in=[
                ORDER_STATUS.CLOSED.value,
                ORDER_STATUS.REJECTED.value
            ]
        )

        start_date, end_date = request.GET.get("start_date", ''), request.GET.get("end_date", '')
        inst = request.user.get_institution()
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date + " 00:00:00", end_date + " 23:59:59"], item_groups__institution=inst)
        else:
            today = datetime.today()
            queryset = queryset.filter(created_at__range=[f'{today.year}-{today.month}-01 00:00:00',
                                                      f'{today.year}-{today.month}-'
                                                      f'{calendar.monthrange(today.year, today.month)[1]} 23:59:59'], item_groups__institution=inst)
        
        paginator = OptionalPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = OrderRestaurantSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = OrderRestaurantSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False)
    def order_stats(self, request):
        start_date, end_date = request.GET.get("start_date", ''), request.GET.get("end_date", '')
        inst = request.user.get_institution()
        if start_date and end_date:
            orders = Order.objects.filter(created_at__range=[start_date + " 00:00:00", end_date + " 23:59:59"], item_groups__institution=inst)
        else:
            today = datetime.today()
            orders = Order.objects.filter(created_at__range=[f'{today.year}-{today.month}-01 00:00:00',
                                                      f'{today.year}-{today.month}-'
                                                      f'{calendar.monthrange(today.year, today.month)[1]} 23:59:59'], item_groups__institution=inst)
        stats = orders.extra({
            'day': "EXTRACT(DAY FROM order_order.created_at)",
        }).values("day").annotate(
            total_orders=Count("id"),
            total_sum1=Sum("products_sum"),
            # avg_preparation_time=Avg(F("prepared_at") - F("created_at"))
        ).order_by("day")
        total_cheque = stats.aggregate(Count('id')).get("id__count")
        accepted_cheque = stats.filter(status='closed').aggregate(Count('id')).get("id__count")
        canceled_cheque = stats.filter(status='rejected').aggregate(Count('id')).get("id__count")
        total_sum = orders.filter(payment_method__in=['cash', 'payme'], status='closed').aggregate(Sum('products_sum'))['products_sum__sum'] or 0
        cash_sum = orders.filter(payment_method='cash', status='closed').aggregate(Sum('products_sum'))['products_sum__sum'] or 0
        payme_sum = orders.filter(payment_method='payme', status='closed').aggregate(Sum('products_sum'))['products_sum__sum'] or 0

        return Response({
            'total': total_cheque,
            'accepted': accepted_cheque,
            'rejected': canceled_cheque,
            'cash_sum': cash_sum,
            'payme_sum': payme_sum,
            'total_sum': total_sum,
            'data': stats
        })


class FeedbackViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InstitutionFeedbackSerializer

    def get_queryset(self):
        inst = self.request.user.get_institution()
        return InstitutionFeedback.objects.filter(institution=inst).order_by('-id')