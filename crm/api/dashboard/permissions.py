from rest_framework.request import Request
from user.models import User
from crm.permissions import CRMPermission


class DashboardPermission(CRMPermission):
    def has_permission(self, request: Request, view):
        is_admin = super().has_permission(request, view)
        user: User = request.user
        if view.action == "get_orders_count_by_status" and user.type == "logist":
            return True
        dashboard_access = user.type == "operator"
        return is_admin or dashboard_access
