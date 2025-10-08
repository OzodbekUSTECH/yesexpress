from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from django.utils.translation import gettext_lazy as _


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "type")}),
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_staff", "is_superuser"),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "password1", "password2"),
            },
        ),
    )
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = (
        "phone_number",
        "first_name",
        "last_name",
    )
    ordering = ("phone_number",)
    list_display = (
        "phone_number",
        "first_name",
        "last_name",
        "type",
    )
    filter_horizontal = ("user_permissions",)
