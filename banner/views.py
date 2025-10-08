from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ViewSetMixin
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination

from .filters import BannerFilter
from .models import Banner
from .serializers import BannerSerializer


class BannerViewSet(ViewSetMixin, ListAPIView):
    serializer_class = BannerSerializer
    queryset = Banner.objects.filter(is_active=True).all()

    filter_backends = (DjangoFilterBackend,)
    filter_fields = ("restaurants",)
    filterset_class = BannerFilter

    pagination_class = LimitOffsetPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['lat'] = self.request.query_params.get('lat')
        context['long'] = self.request.query_params.get('long')
        return context
    # permission_classes = [IsAuthenticated]

    # def get_queryset(self):
    #     return self.request.user.address_set

    # def perform_create(self, serializer):
    #     serializer.save(customer=self.request.user)
