from rest_framework.permissions import BasePermission
from .models import Courier


class IsCourier(BasePermission):
    def has_permission(self, request, view):
        return Courier.objects.filter(user=request.user).exists()
