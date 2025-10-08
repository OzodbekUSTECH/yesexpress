from django.contrib import admin
from .models import Settings

# Register your models here.


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    pass
