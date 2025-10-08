from django.contrib.auth.mixins import AccessMixin
from django.views import View

from product.models import Product


class IsInstitutionAdminMixin(View, AccessMixin):
    """Checks if user is admin or owner of institution"""

    permission_denied_message = "У вас нет доступа к этой странице"
    login_url = "login"
    allowed_user_types = ["institution_admin", "institution_owner", "institution_worker", "institution_admin"]

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        print(request.user.type)
        if (not user.is_authenticated) or (user.type not in self.allowed_user_types):
            return super(IsInstitutionAdminMixin, self).handle_no_permission()

        if user.type in ["institution_admin", "institution_owner", "institution_worker"]:
            try:
                user.get_institution()
            except Exception:
                raise super(IsInstitutionAdminMixin, self).handle_no_permission()

        return super(IsInstitutionAdminMixin, self).dispatch(request, *args, **kwargs)


class IsInstitutionOwnerMixin(IsInstitutionAdminMixin):
    """Checks if user is owner of institution"""

    allowed_user_types = ["institution_owner"]


class IsOperatorMixin(IsInstitutionAdminMixin):
    allowed_user_types = ["main_admin", "admin", "operator"]


class IsOperatorOrLogistMixin(IsInstitutionAdminMixin):
    allowed_user_types = ["main_admin", "admin", "operator", "logist"]


class IsContentManagerMixin(AccessMixin, View):
    permission_denied_message = "У вас нет доступа к этой странице"
    login_url = "login"
    allowed_user_types = ["main_admin", "admin", "content_manager"]

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_anonymous or user.type not in self.allowed_user_types:
            return super().handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class HaveAccessToOrderMixin(AccessMixin, View):
    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if user.is_anonymous or user.type not in [
            "main_admin",
            "admin",
            "operator",
            "logist",
            "institution_owner",
            "institution_admin",
        ]:
            return super().handle_no_permission()

        return super(HaveAccessToOrderMixin, self).dispatch(request, *args, **kwargs)


class HaveAccessToProductMixin(IsInstitutionAdminMixin):
    """Checks if user has access to product"""

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        product_id = kwargs["pk"]
        product = Product.objects.get(pk=product_id)
        if user.is_authenticated and (user.type in self.allowed_user_types):
            if product.category.institution != user.get_institution():
                return super(HaveAccessToProductMixin, self).handle_no_permission()
        return super(HaveAccessToProductMixin, self).dispatch(request, *args, **kwargs)
