from django.urls import path
from . import views


urlpatterns = [
    path(
        "storie-list/",
        views.StoriesViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "storie-detail/<int:pk>/",
        views.StoriesViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "delete": "destroy",
            }
        ),
    ),
]
