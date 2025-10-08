from django.urls import path

from . import views

urlpatterns = [
    path("promo_code/", views.PromoCodeView.as_view({"get": "list", "post": "create"})),
    path(
        "promo_code/<int:pk>/",
        views.PromoCodeView.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
    ),
]
