from django.contrib import admin

from .models import Banner


class BannerAdmin(admin.ModelAdmin):
    fields = ["img", "image"]
    # list_display = ['image', 'img']
    readonly_fields = ["image"]


admin.site.register(Banner, BannerAdmin)
