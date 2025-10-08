from django.urls import path

from . import views

urlpatterns = [
    path("order-groups/", views.OrderItemGroupViewSet.as_view({"get": "list"})),
    path("order-groups/<int:pk>/", views.OrderItemGroupViewSet.as_view({"get": "retrieve"})),
    path("orders/", views.OrderViewSet.as_view({"get": "list"})),
    path("orders/report/", views.ReportAPIView.as_view(), name='order-report'),
    path("orders/<int:pk>/status/", views.OrderViewSet.as_view({"put": "update_status"})),
    path("orders/<int:pk>/courier/", views.OrderViewSet.as_view({"put": "change_courier"})),
    path("order-items/", views.OrderItemViewSet.as_view({"get": "list", "post": "create"})),
    path("order-items/<int:pk>/", views.OrderItemViewSet.as_view({"get": "retrieve", "put": "partial_update", "delete": "destroy"})),
    path("order/feedback/institution/", views.InstitutionFeedbackViewSet.as_view({"get": "list"})),
    path("order/feedback/courier/", views.CourierFeedbackViewSet.as_view({"get": "list"})),
    path("order/stats/", views.OrderStatsView.as_view(), name="order-stats"),
]
