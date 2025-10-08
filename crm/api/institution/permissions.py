from rest_framework.request import Request
from user.models import User
from crm.permissions import CRMPermission
from rest_framework.viewsets import ModelViewSet


class InstitutionPermission(CRMPermission):
    def has_permission(self, request: Request, view: ModelViewSet):
        is_admin = super().has_permission(request, view)
        user: User = request.user
        action = view.action
        allowed_user_types = ["institution_owner", "institution_admin"]
        if action == "list":    
            allowed_user_types.append("operator")
            allowed_user_types.append("logist")
        if not (action == "destroy"):
            allowed_user_types.append("content_manager")
        institution_access = user.type in allowed_user_types
        return is_admin or institution_access
