from django.urls import reverse
from django.views.generic import ListView, UpdateView, TemplateView

from courier.models import Courier
from crm.forms import CourierUpdateForm
from crm.mixins import IsOperatorMixin, IsOperatorOrLogistMixin
from order.models import OrderItemGroup


class OrdersView(IsOperatorMixin, ListView):
    template_name = "crm/new_orders.html"
    queryset = (
        OrderItemGroup.objects.select_related("order", "order__customer")
        .filter(order__status="created")
        .order_by("-created_at")
    )
    context_object_name = "orders"


class OrdersHistoryView(IsOperatorMixin, ListView):
    template_name = "crm/operator_orders_history.html"
    queryset = OrderItemGroup.objects.select_related("order", "order__customer").order_by(
        "-created_at"
    )
    context_object_name = "orders"

    def get_queryset(self):
        status = self.request.GET.get("order_status")
        queryset = super().get_queryset()
        if status:
            queryset = queryset.filter(order__status=status)
        return queryset


class CourierListView(IsOperatorOrLogistMixin, ListView):
    template_name = "crm/couriers.html"
    queryset = Courier.objects.all()
    context_object_name = "couriers"


class CourierUpdateView(IsOperatorOrLogistMixin, UpdateView):
    template_name = "crm/courier_update.html"
    queryset = Courier.objects.all()
    form_class = CourierUpdateForm

    def get_success_url(self):
        courier_id = self.get_object().id

        return reverse("courier-update", kwargs={"pk": courier_id})


class CourierCreateView(IsOperatorOrLogistMixin, TemplateView):
    template_name = "crm/courier_create.html"


class CourierOrderView(IsOperatorOrLogistMixin, TemplateView):
    template_name = "crm/courier_orders.html"
