from rest_framework.permissions import AllowAny
from rest_framework.generics import ListAPIView, RetrieveAPIView
from stories.models import Stories
from .serializers import StoriesSerializer
from django.utils.timezone import now


# Create your views here.


class StoriesList(ListAPIView):
    # queryset = Stories.objects.filter(is_active=True).all()
    serializer_class = StoriesSerializer
    permission_classes = [
        AllowAny,
    ]
    

    def get_queryset(self):
        return Stories.objects.filter(
            is_active=True,
            start_date__lte=now(),
        ).filter(
            end_date__gte=now()
        )
    


class StoriesDetail(RetrieveAPIView):
    queryset = Stories.objects.all()
    serializer_class = StoriesSerializer
    permission_classes = [
        AllowAny,
    ]
