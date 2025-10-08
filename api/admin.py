from django.contrib import admin

from .models import LastVersions


@admin.register(LastVersions)
class LastVersionsAdmin(admin.ModelAdmin):
    list_display = ["__str__", "android_version", "ios_version"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
