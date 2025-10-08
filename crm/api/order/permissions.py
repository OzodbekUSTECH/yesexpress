from rest_framework.request import Request
from user.models import User
from crm.permissions import CRMPermission


class OrderPermission(CRMPermission):
    def has_permission(self, request: Request, view):
        is_admin = super().has_permission(request, view)
        user: User = request.user
        types = ["institution_owner", "institution_admin", "operator", "logist"]
        order_access = user.type in types
        return is_admin or order_access
