from django.urls import path
from . import views

urlpatterns = [
    path("notification/", views.NotificationView.as_view(), name="notification"),
    path("settings/", views.SettingsUpdateView.as_view(), name="settings"),
    path(
        "auth-check/",
        views.CheckAuthView.as_view(),
    ),
]
