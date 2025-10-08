from django.urls import re_path

from .consumers import CourierConsumer, InstitutionConsumer, OrderConsumer, OperatorConsumer

websocket_urlpatterns = [
    re_path("ws/institution/(?P<institution_id>\d+)/$", InstitutionConsumer.as_asgi()),
    re_path("ws/client/(?P<client_id>\d+)/$", OrderConsumer.as_asgi()),
    re_path("ws/operator/$", OperatorConsumer.as_asgi()),
    re_path("ws/courier/$", CourierConsumer.as_asgi()),
]
