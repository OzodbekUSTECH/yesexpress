from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count, F
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, UpdateView, CreateView

from crm.forms import (
    ProductForm,
    CategoryForm,
    InstitutionForm,
    InstitutionAdminForm,
    InstitutionAddressForm,
    DeliverySettingsForm,
    ChangePasswordForm,
    InstitutionOrderReportFilterForm,
    OptionItemFormSet,
    OptionForm,
)
from order.models import OrderItemGroup
from order.status_controller import update_order_status, cancel_order
from product.models import Product, ProductCategory, ProductOption
from . import helpers, filters
from .mixins import (
    IsInstitutionAdminMixin,
    IsInstitutionOwnerMixin,
    HaveAccessToProductMixin,
    IsOperatorMixin,
    HaveAccessToOrderMixin,
)


class RedirectView(View):
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_anonymous:
            return redirect(reverse("login"))

        if user.type in ["main_admin", "admin", "operator"]:
            return redirect(reverse("dashboard"))
        if user.type == "logist":
            return redirect(reverse("courier-list"))
        if user.type in ["institution_admin", "institution_owner"]:
            return redirect(reverse("new-orders"))
        else:
            raise PermissionDenied


# login


class LoginView(View):
    """Login to crm view"""

    def get(self, request):
        return render(request, "crm/login.html")

    def post(self, request):
        phone_number = request.POST.get("phone_number", None)
        password = request.POST.get("password", None)
        if phone_number and password:
            user = authenticate(phone_number=phone_number, password=password)
            if user is not None:
                login(request, user)
                return redirect("new-orders")
            else:
                context = {
                    "login_error": "Имя пользователя и/или пароль введены неверно. Пожалуйста, проверьте данные и попробуйте еще раз.",
                    "username": phone_number,
                }
                return render(request, "crm/login.html", context)


class CRMLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        logout(request)
        return redirect(reverse("login"))


class ChangePasswordView(LoginRequiredMixin, View):
    def post(self, request):
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, "Ваш пароль был успешно изменен")
            return redirect("change-password")
        else:
            messages.error(request, "Произошла ошибка")
        return render(request, "crm/change_password.html", {"form": form})

    def get(self, request):
        form = ChangePasswordForm(request.user)
        return render(request, "crm/change_password.html", {"form": form})


class AdminIndexView(IsInstitutionAdminMixin, TemplateView):
    """Main admin page"""

    template_name = "crm/index.html"


class DashboardView(IsOperatorMixin, TemplateView):
    template_name = "crm/dashboard.html"


# institution


class InstitutionView(IsInstitutionAdminMixin, DetailView):
    """Info about institution view"""

    template_name = "crm/institution.html"
    context_object_name = "institution"

    def get_object(self, queryset=None):
        return self.request.user.get_institution()

    def post(self, request):
        obj = self.get_object()
        obj.is_open = not obj.is_open
        obj.save()
        return redirect(reverse("institution-admin"))


class InstitutionUpdateView(IsInstitutionOwnerMixin, UpdateView):
    """Institution editing view"""

    template_name = "crm/institution_update.html"
    form_class = InstitutionForm

    def get_object(self, queryset=None):
        return self.request.user.get_institution()

    def get_success_url(self):
        return reverse("institution-admin")


class InstitutionManagement(IsInstitutionOwnerMixin, DetailView):
    """Institution administration"""

    template_name = "crm/management.html"
    context_object_name = "institution"

    def get_object(self, queryset=None):
        return self.request.user.get_institution()

    def post(self, request):
        obj = self.get_object()
        action = request.POST.get("action")
        if action == "delete":
            obj.admin = None
            obj.save()
        return redirect(reverse("institution-management"))


class InstitutionAdminCreate(IsInstitutionOwnerMixin, CreateView):
    """admin creation"""

    template_name = "crm/admin_create.html"
    form_class = InstitutionAdminForm

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            institution = request.user.get_institution()
            form = form.save(commit=False)
            form.type = "institution_admin"
            institution.admin = form
            form.save()
            institution.save()

            return redirect(reverse("institution-management"))
        else:
            return render(request, self.template_name, context={"form": form})


class InstitutionAddressView(IsInstitutionOwnerMixin, UpdateView):
    """Address and location update"""

    template_name = "crm/address.html"
    form_class = InstitutionAddressForm

    def get_object(self, queryset=None):
        return self.request.user.get_institution().address

    def get_success_url(self):
        return reverse("institution-admin")


class DeliverySettingsUpdate(IsInstitutionAdminMixin, UpdateView):
    template_name = "crm/delivery_settings.html"
    form_class = DeliverySettingsForm
    success_url = reverse_lazy("institution-admin")

    def get_object(self, queryset=None):
        return self.request.user.get_institution().delivery_settings


# orders


class NewOrdersView(IsInstitutionAdminMixin, ListView):
    """List of not accepted orders. Powered by Firebase"""

    template_name = "crm/new_orders.html"
    queryset = OrderItemGroup.objects.select_related("order", "order__customer")
    context_object_name = "orders"

    # def dispatch(self, request, *args, **kwargs):
    #     user = request.user
    #     if user.type == 'operator':
    #         return redirect(reverse('operator-orders'))
    #     return super(NewOrdersView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.queryset.filter(
            institution=self.request.user.get_institution(), order__status="created"
        ).order_by("-created_at")


class CategoryListView(IsInstitutionAdminMixin, ListView):
    """List of institution categories"""

    template_name = "crm/categories.html"
    context_object_name = "category_set"

    def get_queryset(self):
        return self.request.user.get_institution().category_set.all()


class CategoryCreateView(IsInstitutionAdminMixin, CreateView):
    """New category creation view"""

    queryset = ProductCategory.objects.all()
    template_name = "crm/category_create.html"
    form_class = CategoryForm

    def get_success_url(self):
        return reverse("categories")


class CategoryUpdateView(IsInstitutionAdminMixin, UpdateView):
    queryset = ProductCategory.objects.all()
    template_name = "crm/category_update.html"
    form_class = CategoryForm

    def get_queryset(self):
        institution = self.request.user.get_institution()
        return self.queryset.filter(institution=institution)

    def get_success_url(self):
        return reverse("categories")


class CategoryDeleteView(IsInstitutionAdminMixin, View):
    """Category deletion"""

    def post(self, request):
        category_id = request.POST.get("category_id")
        ProductCategory.objects.get(pk=category_id).delete()
        return redirect(reverse("categories"))


class ProductListView(IsInstitutionAdminMixin, ListView):
    """List of institution products"""

    template_name = "crm/products.html"

    def get_queryset(self):
        return Product.objects.filter(
            category__in=self.request.user.get_institution().category_set.all()
        ).select_related("category")


class ProductDetailView(HaveAccessToProductMixin, DetailView):
    """Info about product and its options"""

    queryset = Product.objects.all().prefetch_related("options")
    template_name = "crm/product_detail.html"


class ProductCreateView(IsInstitutionAdminMixin, CreateView):
    """Product creation view"""

    queryset = Product.objects.all()
    template_name = "crm/product_create.html"
    form_class = ProductForm

    def form_valid(self, form):
        if form.is_valid():
            form = form.save(commit=False)
            form.institution = self.request.user.get_institution()
            form.save()
            return redirect(reverse("product-detail-admin", kwargs={"pk": form.id}))


class ProductUpdateView(HaveAccessToProductMixin, UpdateView):
    """Product edition view"""

    queryset = Product.objects.all()
    form_class = ProductForm
    template_name = "crm/product_update.html"

    def get_success_url(self):
        pk = self.kwargs.get("pk")
        return reverse("product-detail-admin", kwargs={"pk": pk})


class OptionView(IsInstitutionAdminMixin, View):
    """Option creation and deletion"""

    # TODO: add option edition

    def post(self, request, *args, **kwargs):
        actions = {
            "create": helpers.create_option,
            "update": helpers.update_option,
            "delete": helpers.delete_option,
        }

        return actions[request.POST.get("action")](request)


def update_option_items(request, pk):
    option = ProductOption.objects.get(pk=pk)
    if request.method == "POST":
        formset = OptionItemFormSet(request.POST, request.FILES, instance=option)
        form = OptionForm(request.POST, request.FILES, instance=option)
        if formset.is_valid() and form.is_valid():
            formset.save()
            form.save()
            return redirect(option.get_absolute_url())
    else:
        form = OptionForm(instance=option)
        formset = OptionItemFormSet(instance=option)
    return render(request, "crm/option_update.html", {"formset": formset, "form": form})


class OrderListView(IsInstitutionAdminMixin, ListView):
    """All orders list"""

    template_name = "crm/orders.html"
    context_object_name = "orders"
    queryset = OrderItemGroup.objects.select_related("order", "order__customer")

    def get_queryset(self):
        status = self.request.GET.get("status")
        queryset = (
            self.queryset.filter(institution=self.request.user.get_institution())
            .exclude(order__status="pending")
            .order_by("-created_at")
        )
        if status:
            queryset = queryset.filter(order__status=status)

        return queryset


class OrderDetailView(HaveAccessToOrderMixin, DetailView):
    """Info about order"""

    queryset = (
        OrderItemGroup.objects.all()
        .prefetch_related("items", "items__product", "items__options")
        .select_related("order__customer")
    )
    template_name = "crm/order_detail.html"
    context_object_name = "order"

    def post(self, request, *args, **kwargs):
        """Change status of order"""

        order_item_group_id = kwargs["pk"]
        status = request.POST.get("status")
        order_item_group = OrderItemGroup.objects.get(pk=order_item_group_id)
        if status:
            if status == "rejected":
                cancel_order(order_item_group.order, ignore_constraints=True)
            else:
                update_order_status(order_item_group.order, status)

        return redirect(reverse("order-detail-admin", kwargs={"pk": order_item_group_id}))


class OrderReportView(IsInstitutionAdminMixin, ListView):
    template_name = "crm/order_report.html"
    queryset = (
        OrderItemGroup.objects.filter(order__status="closed")
        .annotate(without_commission=F("products_sum") - F("commission"))
        .select_related("order__customer", "order")
    )
    context_object_name = "orders"

    def get_queryset(self):
        queryset = super().get_queryset().filter(institution=self.request.user.get_institution())
        filter = filters.InstitutionOrderFilter(self.request.GET)
        if filter.is_valid():
            queryset = filter.filter_queryset(queryset)
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super()
        dct = self.get_queryset().aggregate(
            total_sum=Sum("without_commission", default=0),
            commission_sum=Sum("commission", default=0),
            products_sum=Sum("products_sum", default=0),
            count=Count("id"),
        )
        context.update({"form": InstitutionOrderReportFilterForm(self.request.GET), **dct})
        return context
