import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class CourierLocationConsumer(WebsocketConsumer):
    def connect(self):
        self.courier_id = self.scope["url_route"]["kwargs"]["courier_id"]
        self.courier_group_name = f"courier_{self.courier_id}"
        async_to_sync(self.channel_layer.group_add)(self.courier_group_name, self.channel_name)

        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        async_to_sync(self.channel_layer.group_send)(
            self.courier_group_name,
            {
                "type": "send_location",
                "text": text_data,
            },
        )

    def send_location(self, event):
        text_data = json.dumps(event)
        self.send(text_data=text_data)

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(self.courier_group_name, self.channel_name)


class ReadyOrdersConsumer(WebsocketConsumer):
    def connect(self):
        async_to_sync(self.channel_layer.group_add)("ready_orders", self.channel_name)

        self.accept()

    def send_order_status(self, event):
        text_data = json.dumps(event)
        self.send(text_data)
