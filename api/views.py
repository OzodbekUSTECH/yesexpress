from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import LastVersions


class SearchView(APIView):
    def get(self, *args, **kwargs):
        search_text = self.request.query_params.get("search")
        return Response(data=services.search_results(search_text, self.request))


class GetLastVersionsView(APIView):
    def get(self, request):
        version = LastVersions.objects.first()
        return Response(
            data={"android_version": version.android_version, "ios_version": version.ios_version}
        )
