from django.contrib import admin

from .models import InstitutionFeedback, DeliveryFeedback


class NoAddEditPermissionMixin:
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(InstitutionFeedback)
class InstitutionFeedbackAdmin(NoAddEditPermissionMixin, admin.ModelAdmin):
    pass


@admin.register(DeliveryFeedback)
class DeliveryFeedback(NoAddEditPermissionMixin, admin.ModelAdmin):
    pass
