from django.urls import path

from . import views

urlpatterns = [
    path("banners/", views.BannerView.as_view({"get": "list", "post": "create"})),
    path(
        "banners/<int:pk>/",
        views.BannerView.as_view({"get": "retrieve", "put": "partial_update", "delete": "destroy"}),
    ),
]
