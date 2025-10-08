from django.urls import path
from . import views

urlpatterns = [
    path(
        "settings/",
        views.SettingsViewSet.as_view(
            {
                "get": "list",
                "put": "update",
            }
        ),
        name="settings",
    ),
]
