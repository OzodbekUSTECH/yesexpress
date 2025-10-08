from django.urls import path

from . import views

urlpatterns = [
    path(
        "regions/",
        views.RegionViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "regions/<int:pk>/",
        views.RegionViewSet.as_view(
            {
                "get": "retrieve",
                "put": "partial_update",
            }
        ),
    ),
    path(
        "institution-addresses/",
        views.InstitutionAddressViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "institution-addresses/<int:pk>/",
        views.InstitutionAddressViewSet.as_view(
            {
                "get": "retrieve",
                "put": "partial_update",
            }
        ),
    ),
]
