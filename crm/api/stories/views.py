from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from stories.models import Stories, StoriesToRegion
from .serializers import CrmStoriesSerializer, CrmStoriesCreateSerializer
from stories.api_views import MultiStoriesSerializerViewSetMixin
from rest_framework.viewsets import ModelViewSet

from .services import create_stories, update_stories
from .permissions import StoriesPermission

# Create your views here.


class StoriesViewSet(MultiStoriesSerializerViewSetMixin, ModelViewSet):
    queryset = Stories.objects.all()
    serializer_action_classes = {
        "list": CrmStoriesSerializer,
        "retrieve": CrmStoriesSerializer,
        "create": CrmStoriesCreateSerializer,
        "update": CrmStoriesCreateSerializer,
    }
    permission_classes = [IsAuthenticated, StoriesPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.select_related("created_user", "institution__address").prefetch_related(
            Prefetch("regions", StoriesToRegion.objects.select_related("region"))
        )
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stories_instance = create_stories(user=request.user, **serializer.validated_data)
        serializer.instance = stories_instance
        return Response(serializer.data, status=201)

    def update(self, request, *args, **kwargs):
        stories_instance = self.get_object()
        serializer = self.get_serializer(instance=stories_instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        stories_instance = update_stories(stories_instance, serializer.validated_data)
        serializer.instance = stories_instance
        return Response(serializer.data)
