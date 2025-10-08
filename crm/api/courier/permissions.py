from rest_framework.request import Request
from user.models import User
from crm.permissions import CRMPermission
from courier.models import Courier


class CourierPermission(CRMPermission):
    def has_permission(self, request: Request, view):
        user: User = request.user
        is_admin = super().has_permission(request, view)
        is_courier = Courier.objects.filter(user=user).exists()
        is_logist = user.type == "logist" or user.type == "operator"
        return is_admin or is_courier or is_logist
        