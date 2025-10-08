import json
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import UpdateAPIView
from rest_framework.views import APIView

from .models import Settings
from .serializers import SettingsSerializer
from order.push_notifications.consumers import send_notification_to_all, send_notification_by_phone_number

# Create your views here.


class SettingsUpdateView(UpdateAPIView):
    serializer_class = SettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Settings.load()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CheckAuthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({"message": "OK"})

class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        title = request.data.get('title', 'test')
        body = request.data.get('body', "Barcha foydalanuvchilarga muhim yangilik.")
        data = request.data.get('data', {"type": "general"})
        app = request.data.get('app')
        to = request.data.get('to')
        if to == 'all':
            result = send_notification_to_all(title, body, data, app)
        if to != 'all':
            result = send_notification_by_phone_number(to, title, body, data, app)
            
        return Response({"message": result})
