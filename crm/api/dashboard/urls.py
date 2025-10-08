from django.urls import path

from . import views

urlpatterns = [
    path(
        "dashboard/orders-by-status/",
        views.DashboardOrdersViewSet.as_view({"get": "get_orders_count_by_status"}),
    ),
    path(
        "dashboard/completed-orders-graph/",
        views.DashboardOrdersViewSet.as_view({"get": "get_completed_orders_graph_data"}),
    ),
    path(
        "dashboard/new-orders-graph/",
        views.DashboardOrdersViewSet.as_view({"get": "new_orders_graph_data"}),
    ),
]
