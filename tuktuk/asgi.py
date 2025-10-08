"""
ASGI config for tuktuk project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tuktuk.settings")
django.setup()

from order.websocket_urls import websocket_urlpatterns as order_urls
from order.consumers import TelegramBotConsumer
from order.push_notifications.consumers import FirebaseConsumer
from courier.websocket_urls import websocket_urlpatterns as courier_urls

websocket_urlpatterns = order_urls + courier_urls

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
        "channel": ChannelNameRouter(
            {
                "telegram-notify": TelegramBotConsumer.as_asgi(),
                "firebase-notify": FirebaseConsumer.as_asgi(),
            }
        ),
    }
)
