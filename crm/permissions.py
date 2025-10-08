from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from user.models import User
from courier.models import Courier


class CRMPermission(BasePermission):
    def has_permission(self, request: Request, view):
        user: User = request.user
        return user.type in ["main_admin", "admin", "institution_worker", "institution_admin"]
