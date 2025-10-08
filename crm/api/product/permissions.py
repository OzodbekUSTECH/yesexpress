from rest_framework.request import Request
from user.models import User
from crm.permissions import CRMPermission


class ProductPermission(CRMPermission):
    def has_permission(self, request: Request, view):
        is_admin = super().has_permission(request, view)
        user: User = request.user
        product_access = user.type in ["content_manager", "institution_owner", "institution_admin", "operator"]
        return is_admin or product_access
