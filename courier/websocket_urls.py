from django.urls import re_path
from .consumers import CourierLocationConsumer, ReadyOrdersConsumer

websocket_urlpatterns = [
    re_path("ws/courier-location/(?P<courier_id>\d+)/$", CourierLocationConsumer.as_asgi()),
    re_path("ws/ready_orders/", ReadyOrdersConsumer.as_asgi()),
]
