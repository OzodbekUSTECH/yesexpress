from django.db.models import F, Sum, Count
from django.db.models.functions import TruncDay
from django.views.generic import ListView, TemplateView

from crm.filters import OrderFilter
from crm.forms import OrderFilterForm
from order.models import OrderItemGroup


class OrderReportView(ListView):
    template_name = "admin_extensions/order_reports.html"
    queryset = OrderItemGroup.objects.annotate(
        without_commission=F("products_sum") - F("commission")
    ).select_related("order__customer", "order", "institution")
    context_object_name = "order_list"

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .order_by("-order__created_at")
            .annotate(f_created_at=TruncDay("order__created_at"))
        )

        filter = OrderFilter(self.request.GET)
        if filter.is_valid():
            queryset = filter.filter_queryset(queryset)

        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super()
        dct = self.get_queryset().aggregate(
            without_commission_sum=Sum("without_commission", default=0),
            commission_sum=Sum("commission", default=0),
            products_sum=Sum("products_sum", default=0),
            delivering_sum=Sum("delivering_sum", default=0),
            total_sum=Sum("total_sum", default=0),
            count=Count("id"),
        )
        context.update({"form": OrderFilterForm(self.request.GET), **dct})

        return context


class UserCheckView(TemplateView):
    template_name = "user_check.html"
