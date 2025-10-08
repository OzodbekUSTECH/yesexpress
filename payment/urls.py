from django.urls import path
from . import views

urlpatterns = [
    path("payments/", views.PaymentViewSet.as_view({"get": "list"})),
    path("payments/<int:pk>/", views.PaymentViewSet.as_view({"get": "retrieve"})),
]
