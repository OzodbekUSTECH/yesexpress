from rest_framework.viewsets import ModelViewSet

from banner.models import Banner
from base.api_views import MultiSerializerViewSetMixin
from crm.api.banner.serializers import CrmBannerSerializer


class BannerView(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = CrmBannerSerializer
