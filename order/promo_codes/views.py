from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from order.promo_codes.serializers import PromoCodeInfoSerializer, GetPromoCodeInfoSerializer


@swagger_auto_schema(
    operation_description="Get promo code info",
    operation_id="promo-codes_get-promo-code-info",
    responses={400: "promocode does not exist", 200: PromoCodeInfoSerializer()},
    request_body=GetPromoCodeInfoSerializer,
    method="post",
)
@api_view(http_method_names=["POST"])
@permission_classes([IsAuthenticated])
def get_promo_code_info(request):
    serializer = GetPromoCodeInfoSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    promo_code = serializer.validated_data["promo_code"]
    return Response(PromoCodeInfoSerializer(instance=promo_code).data)
