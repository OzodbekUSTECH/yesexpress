from django.urls import path

from . import views

urlpatterns = [
    path(
        "delivery-settings/",
        views.DeliverySettingsViewSet.as_view({"get": "retrieve", "put": "partial_update"}),
    ),
    path(
        "couriers/",
        views.CourierViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "couriers/<int:pk>/",
        views.CourierViewSet.as_view(
            {"get": "retrieve", "put": "partial_update", "delete": "destroy"}
        ),
    ),
    path(
        "couriers/stats/",
        views.CourierViewSet.as_view(
            {
                "get": "stats",
            }
        ),
    ),
]
