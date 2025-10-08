from django.db.models import Q, F
from institution.models import Institution, InstitutionBranch

from rest_framework import viewsets, views
from rest_framework import mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSetMixin
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.decorators import action

from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.db.models import Func, PointField



from .serializers import ProductDetailSerializer, ProductListSerializer, CategoryListSerializer
from .models import Product, LikedProducts, ProductCategory, ProductToBranch


class ProductCategoryViewSet(ViewSetMixin, ListAPIView, RetrieveAPIView):
    serializer_class = CategoryListSerializer
    queryset = ProductCategory.objects.filter(
        is_deleted=False, is_active=True, institution__is_deleted=False
    )


class ProductViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.filter(
        is_deleted=False, institution__is_deleted=False, status='active').prefetch_related("options", "options__items")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_authenticated:
            return queryset.annotate(
                is_liked=Q(id__in=user.liked_products.values_list("product_id", flat=True))
            )
        return queryset
    
    @action(detail=False, methods=["post"], url_path="available")
    def available(self, request):
        product_ids = request.data.get("product_ids", [])
        institution = request.data.get("institution")
        
        
        lat = float(request.data.get("lat", 0))
        long = float(request.data.get("long", 0))

        user_point = Point(lat, long, srid=4326)
        
        if not isinstance(product_ids, list):
            return Response({"status": "error","detail": "product_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not institution:
            return Response({"status": "error","detail": "institution required"}, status=status.HTTP_400_BAD_REQUEST)
        
        institution = Institution.objects.get(pk=institution)
        closest_branch = (
            InstitutionBranch.objects.get_available()
            .with_is_open_by_schedule()
            .filter(institution=institution, is_active=True, is_open=True)
            .annotate(
                branch_point=Func(
                    Func(F("address__latitude"), function="CAST", template="%(function)s(%(expressions)s AS double precision)"),
                    Func(F("address__longitude"), function="CAST", template="%(function)s(%(expressions)s AS double precision)"),
                    function="ST_Point",
                    output_field=PointField(srid=4326)
                ),
                distance=Distance("branch_point", user_point)
            )
            .order_by("distance")
            .first()
        )

        available_product_ids = list(
            ProductToBranch.objects.filter(
                institution_branches=closest_branch,
                is_available=True,
                product__status="active"
            ).values_list("product_id", flat=True)
        )
        
        available_set = set(available_product_ids)
        
        result = {str(pid): pid in available_set for pid in product_ids}

        return Response(result)
    
    @action(detail=False, methods=["get"], url_path="available")
    def available(self, request):
        product_id = request.query_params.get("product_id")
        institution = request.query_params.get("institution")
        
        lat = float(request.query_params.get("lat", 0))
        long = float(request.query_params.get("long", 0))

        user_point = Point(lat, long, srid=4326)
        
        if not product_id:
            return Response({"status": "error","detail": "product_id required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not institution:
            return Response({"status": "error","detail": "institution required"}, status=status.HTTP_400_BAD_REQUEST)
        
        institution = Institution.objects.get(pk=institution)
        closest_branch = (
            InstitutionBranch.objects.get_available()
            .with_is_open_by_schedule()
            .filter(institution=institution, is_active=True, is_open=True)
            .annotate(
                branch_point=Func(
                    Func(F("address__latitude"), function="CAST", template="%(function)s(%(expressions)s AS double precision)"),
                    Func(F("address__longitude"), function="CAST", template="%(function)s(%(expressions)s AS double precision)"),
                    function="ST_Point",
                    output_field=PointField(srid=4326)
                ),
                distance=Distance("branch_point", user_point)
            )
            .order_by("distance")
            .first()
        )

        available_product = ProductToBranch.objects.filter(
            institution_branches=closest_branch,
            is_available=True,
            product__status="active",
            product_id = product_id
        )
        
        if available_product.exists():
            return Response({"status": "ok"}, 200)

        return Response({"status": "unavailable"}, 400)


class LikeProductView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        product_id = pk

        try:
            LikedProducts.objects.get(customer=request.user, product_id=product_id).delete()
            response = Response({"action": "dislike"})

        except LikedProducts.DoesNotExist:
            LikedProducts(customer=request.user, product_id=product_id).save()
            response = Response({"action": "like"})

        return response


class LikedProductsList(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Product.objects.filter(
            id__in=request.user.liked_products.values_list("product_id", flat=True),
            is_deleted=False,
        )
        return Response(
            ProductListSerializer(queryset, many=True, context={"request": request}).data
        )
