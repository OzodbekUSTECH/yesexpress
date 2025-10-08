from django.urls import path, include


from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # JWT Token
    path(
        "users/",
        include(
            [
                # JWT Token
                path("login/", views.CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
                path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
                path("me/", views.ActiveUserViewSet.as_view({"get": "retrieve", "put": "partial_update"})),
                path("me/avatar/", views.ActiveUserViewSet.as_view({"put": "remove_avatar"})),
                path("logout/", views.LogoutDeviceView.as_view()),

            ]
        ),
    ),
    path(
        "workers/",
        include(
            [
                path("", views.WorkerViewSet.as_view({"get": "list", "post": "create"})),
                path(
                    "<int:pk>/",
                    views.WorkerViewSet.as_view({"get": "retrieve", "put": "partial_update", "delete": "destroy"}),
                ),
            ]
        ),
    ),
    path(
        "clients/",
        include(
            [
                path("", views.ClientsViewSet.as_view({"get": "list", "post": "create"})),
                path(
                    "<int:pk>/",
                    views.ClientsViewSet.as_view({"get": "retrieve", "put": "partial_update"}),
                ),
                path("device/", views.RegisterDeviceView.as_view(), name="register-device"),
            ]
        ),
    ),
]
