from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from common.models import Settings
from .serializers import SettingsSerializer

# Create your views here.


class SettingsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        settings_instance = Settings.load()
        serializer = SettingsSerializer(settings_instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        settings_instance = Settings.load()
        serializer = SettingsSerializer(settings_instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
