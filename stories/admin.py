from django.contrib import admin
from .models import Stories

# Register your models here.


@admin.register(Stories)
class StoriesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "image_stories_ru",
        "image_stories_en",
        "image_stories_uz",
        "url_link",
    )
