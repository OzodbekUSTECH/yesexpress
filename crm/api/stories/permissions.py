from rest_framework.request import Request
from user.models import User
from crm.permissions import CRMPermission


class StoriesPermission(CRMPermission):
    def has_permission(self, request: Request, view):
        is_admin = super().has_permission(request, view)
        user: User = request.user
        stories_access = True  # condition here, check who can use this permission

        return is_admin or stories_access
