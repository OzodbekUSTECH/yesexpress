import datetime
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncHour
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.api_views import MultiSerializerViewSetMixin
from crm.api.order.filters import CrmOrderFilter
from order.models import Order
from .permissions import DashboardPermission


class DashboardOrdersViewSet(MultiSerializerViewSetMixin, GenericViewSet):
    queryset = Order.objects.all()
    serializer_action_classes = {}
    permission_classes = [IsAuthenticated, DashboardPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CrmOrderFilter

    def get_orders_count_by_status(self, request):
        orders = self.filter_queryset(self.get_queryset())
        orders = orders.aggregate(
            created=Count("id", filter=Q(status="created")),
            pending=Count("id", filter=Q(status="pending")),
            accepted=Count("id", filter=Q(status="accepted")),
            ready=Count("id", filter=Q(status="ready")),
            shipped=Count("id", filter=Q(status="shipped")),
            closed=Count("id", filter=Q(status="closed")),
            rejected=Count("id", filter=Q(status="rejected")),
        )

        return Response({"status": k, "count": v} for k, v in orders.items())

    def get_completed_orders_graph_data(self, request):
        current_time = datetime.datetime.now()
        start_of_day = datetime.datetime.combine(current_time.date(), datetime.time.min)
        current_hour = current_time.replace(minute=0, second=0, microsecond=0)

        orders = self.filter_queryset(self.get_queryset())
        closed_orders = (
            orders.filter(completed_at__range=[start_of_day, current_time], status="closed")
            .annotate(completed_hour=TruncHour("completed_at"))
            .values("completed_hour")
            .annotate(orders_count=Count("id"))
            .order_by("completed_hour")
        )
        rejected_orders = (
            orders.filter(completed_at__range=[start_of_day, current_time], status="rejected")
            .annotate(completed_hour=TruncHour("completed_at"))
            .values("completed_hour")
            .annotate(orders_count=Count("id"))
            .order_by("completed_hour")
        )

        result_dict = {
            (start_of_day + timedelta(hours=i)).strftime("%H:%M"): dict(
                label=(start_of_day + timedelta(hours=i)).strftime("%H:%M"),
                closed_count=0,
                rejected_count=0,
            )
            for i in range((current_hour - start_of_day).seconds // 3600 + 1)
        }

        for order in closed_orders:
            hour_key = order["completed_hour"].strftime("%H:%M")
            result_dict[hour_key]["closed_count"] = order["orders_count"]

        for order in rejected_orders:
            hour_key = order["completed_hour"].strftime("%H:%M")
            result_dict[hour_key]["rejected_count"] = order["orders_count"]

        return Response(result_dict.values())

    def new_orders_graph_data(self, request):
        current_time = datetime.datetime.now()
        start_of_day = datetime.datetime.combine(current_time.date(), datetime.time.min)
        current_hour = current_time.replace(minute=0, second=0, microsecond=0)

        orders = self.filter_queryset(self.get_queryset())
        new_orders = (
            orders.filter(created_at__range=[start_of_day, current_time], status="created")
            .annotate(created_hour=TruncHour("created_at"))
            .values("created_hour")
            .annotate(orders_count=Count("id"))
            .order_by("created_hour")
        )

        result_dict = {
            (start_of_day + timedelta(hours=i)).strftime("%H:%M"): dict(
                label=(start_of_day + timedelta(hours=i)).strftime("%H:%M"), created_count=0
            )
            for i in range((current_hour - start_of_day).seconds // 3600 + 1)
        }

        for order in new_orders:
            hour_key = order["created_hour"].strftime("%H:%M")
            result_dict[hour_key]["created_count"] = order["orders_count"]

        return Response(result_dict.values())
