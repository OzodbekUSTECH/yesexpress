
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

import threading

from django.db.models import Avg, Q, Prefetch, Exists, OuterRef, F, IntegerField, Case, Value, When, BooleanField, Subquery, Count
from django.db.models.functions import Round, Coalesce
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.db.models import Func, PointField


from order.feedback.models import InstitutionFeedback
from institution.services import seed_category, seed_institution_branch, seed_products

from rest_framework import views
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.viewsets import ViewSetMixin
from rest_framework.decorators import action




from address.models import Address
from product.models import Product, ProductToBranch, ProductCategory
from product.serializers import ProductListSerializer
from rkeeper.services import rkeeperAPI
from .filters import InstitutionFilterSet

from .models import (
    Institution,
    InstitutionCategory,
    LikedInstitutions,
    InstitutionRating,
    InstitutionBranch,
)
from .serializers import (
    InstitutionListSerializer,
    InstitutionDetailSerializer,
    InstitutionCategoryListSerializer,
    InstitutionCategoryDetailSerializer,
)


class InstitutionCategoryViewSet(ViewSetMixin, ListAPIView, RetrieveAPIView):
    queryset = InstitutionCategory.objects.get_available()
    serializer_class = InstitutionCategoryListSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return InstitutionCategoryDetailSerializer
        return InstitutionCategoryListSerializer


class InstitutionViewSet(ViewSetMixin, ListAPIView, RetrieveAPIView):
    queryset = (
        Institution.objects.get_available().select_related("category")
    ).prefetch_related(
        Prefetch('category_set', queryset=ProductCategory.objects.filter(is_active=True, is_deleted=False)),
        Prefetch("branches", InstitutionBranch.objects.select_related("address")),
        Prefetch('product_set', queryset=Product.objects.filter(status='active', is_deleted=False))
    )

    filterset_class = InstitutionFilterSet

    pagination_class = PageNumberPagination

    def get_serializer_class(self):
        if self.action == "list":
            return InstitutionListSerializer
        return InstitutionDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        address_id = self.request.query_params.get("address")
        if address_id:
            context["address"] = Address.objects.get(pk=address_id)
        context["lat"] = self.request.query_params.get("lat", 0)
        context["long"] = self.request.query_params.get("long", 0)
        return context

    def get_queryset(self):
        user_point = Point(float(self.request.query_params.get("lat", 0)), float(self.request.query_params.get("long", 0)), srid=4326)
        
        rating_subquery = InstitutionFeedback.objects.filter(
            institution=OuterRef("pk")
        ).values("institution").annotate(avg_rating=Avg("value")).values("avg_rating")
        
        unique_institutions = InstitutionBranch.objects.filter(
            region_branch__polygon__contains=user_point
        ).values('institution__id').distinct()
        
        min_distance_subquery = InstitutionBranch.objects.filter(
            institution=OuterRef("pk"),
            region_branch__polygon__contains=user_point,
            is_active=True,
            is_deleted=False,
            is_open=True
        ).annotate(
            branch_point=Func(
                Func(F("address__latitude"), function="CAST", template="%(function)s(%(expressions)s AS double precision)"),
                Func(F("address__longitude"), function="CAST", template="%(function)s(%(expressions)s AS double precision)"),
                function="ST_Point",
                output_field=PointField(srid=4326)
            ),
            distance=Distance("branch_point", user_point)
        ).order_by("distance").values("distance")[:1]

        queryset = (
            super(InstitutionViewSet, self)
            .get_queryset()
            .filter(
                id__in=Subquery(unique_institutions)
            )
            .select_related("category", "admin", "owner", "address", "delivery_settings")
            .annotate(
                rating=Round(Subquery(rating_subquery), 2),
                has_active_branch=Case(
                    When(
                        is_open=True,  # institution.is_open
                        then=Exists(
                            InstitutionBranch.objects.get_available().filter(
                                institution=OuterRef("pk"), is_open=True, is_active=True
                            )
                        ),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                is_open_by_schedule=Case(
                    When(
                        is_open=True,
                        then=Exists(
                            InstitutionBranch.objects.with_is_open_by_schedule().filter(
                                institution=OuterRef("pk"), is_open_by_schedule=True, is_open=True, is_active=True
                            )
                        ),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                has_active_branch_weight=Case(
                    When(has_active_branch=True, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                ),
                is_open_weight=Case(
                    When(is_open_by_schedule=True, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                ),
                distance=Subquery(min_distance_subquery)
            )
        )
        
        if self.action == "list":


            queryset = queryset.order_by(
                "has_active_branch_weight",
                "is_open_weight",
                Coalesce("position", Value(999999)),
                "distance"
            )
            
            # Debug: Natijalarni chop etish
            # print("Natijalar:")
            # for institution in queryset:
            #     print(f"ID: {institution.pk}| "
            #         f"Name: {institution.name}| "
            #         f"Has Active Branch: {institution.has_active_branch_weight}| "
            #         f"Is Open: {institution.is_open_weight}| "
            #         f"Position: {institution.position or 'NULL'}| "
            #         f"Distance: {institution.distance}|")

            # Debug: Takrorlanishlarni tekshirish
            # duplicates = queryset.values('pk').annotate(count=Count('pk')).filter(count__gt=1)
            # print("Takrorlangan institutlar:", duplicates)

            # Debug: Har institutning filiallar sonini tekshirish
            # branch_counts = InstitutionBranch.objects.filter(
            #     region_branch__polygon__contains=user_point
            # ).values('institution__pk').annotate(count=Count('pk'))
            # print("Filiallar soni:", branch_counts)
                
            return queryset
        
        return queryset
        
        
    def retrieve(self, request, pk, *args, **kwargs):
        instance = self.get_object()
        lat = float(request.query_params.get("lat", 0))
        long = float(request.query_params.get("long", 0))

        user_point = Point(lat, long, srid=4326)
        
        # print("▶️ Foydalanuvchi joylashuvi:", user_point)

        closest_branch = (
            InstitutionBranch.objects.get_available()
            .with_is_open_by_schedule()
            .filter(institution=instance, is_active=True, is_open=True)
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
        
        if closest_branch:
            # print("✅ Eng yaqin branch topildi:", closest_branch.id, closest_branch, closest_branch.address.reference_point, closest_branch.address.latitude, closest_branch.address.longitude)

            available_product_ids = list(
                ProductToBranch.objects.filter(
                    institution_branches=closest_branch,
                    is_available=True,
                    product__status="active"
                ).values_list("product_id", flat=True)
            )
            
            # print("📦 Mavjud mahsulot IDlari:", available_product_ids, len(available_product_ids))

            filtered_products = Product.objects.filter(
                id__in=available_product_ids,
                status="active",
                is_deleted=False,
                category__institution=instance
            )

            # print("🧾 Filterlangan productlar soni:", len(filtered_products))

            instance = self.get_queryset().prefetch_related(
                Prefetch("category_set__product_set", queryset=filtered_products)
            ).get(pk=instance.pk)

            active_categories = instance.category_set.filter(is_active=True).all().prefetch_related(
                Prefetch("product_set", queryset=filtered_products)
            )

            # print("📂 Aktiv kategoriyalar soni:", active_categories.count())

        # available_product_ids = list(ProductToBranch.objects.filter(
        #     institution_branches__institution=instance,
        #     institution_branches__region_branch__polygon__contains=point,
        #     is_available=True,
        #     product__status="active"
        # ).values_list("product_id", flat=True))

        # filtered_products = Product.objects.filter(id__in=available_product_ids, status="active", category__institution=instance)
            
        # instance = self.get_queryset().prefetch_related(Prefetch("category_set__product_set", queryset=filtered_products)).get(pk=instance.pk)
        # active_categories = instance.category_set.filter(is_active=True).all().prefetch_related(
        #     Prefetch("product_set", queryset=filtered_products)
        # )

        
            
            serializer = InstitutionDetailSerializer(instance, context={"request": request, "active_categories": active_categories})
            return Response(serializer.data)
        else:
            print("❌ Eng yaqin faol branch topilmadi")
        
    @action(detail=False, methods=["get"], url_path="favourite")
    def favourite(self, request):
        user = request.user
        queryset = self.get_queryset().filter(id__in=user.liked_institutions.values_list("institution_id", flat=True))
        serializer = self.get_serializer(queryset, many=True)
        return Response(InstitutionListSerializer(queryset, many=True, context={"request": request}).data)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("category_id", in_=openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                "lat", in_=openapi.IN_QUERY, type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT
            ),
            openapi.Parameter(
                "long", in_=openapi.IN_QUERY, type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT
            )
        ]
    )
    
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RestaurantViewSet(InstitutionViewSet):
    def get_queryset(self):
        user_point = Point(float(self.request.query_params.get("lat", 0)), float(self.request.query_params.get("long", 0)), srid=4326)

        category = self.request.query_params.get('category')
        is_popular = self.request.query_params.get('is_popular')
        queryset = super(RestaurantViewSet, self).get_queryset().filter(type="restaurant")
       
        if category:
            # queryset = queryset.filter(category=category)
            queryset = queryset.filter(Q(category=category) | Q(secondary_categories=category)).distinct()
        if is_popular is not None:
            is_popular = True if is_popular == 'true' else False
            queryset = queryset.filter(is_popular=is_popular)
        

        # min_distance_subquery = InstitutionBranch.objects.filter(
        #     institution=OuterRef("pk"),
        #     region_branch__polygon__contains=user_point
        # ).annotate(
        #     branch_point=Func(
        #         Func(F("address__latitude"), function="CAST", template="%(function)s(%(expressions)s AS double precision)"),
        #         Func(F("address__longitude"), function="CAST", template="%(function)s(%(expressions)s AS double precision)"),
        #         function="ST_Point",
        #         output_field=PointField(srid=4326)
        #     ),
        #     distance=Distance("branch_point", user_point)
        # ).order_by("distance").values("distance")[:1]
                    
        # queryset = queryset.annotate(
        #     distance=Subquery(min_distance_subquery)
        # ).order_by(
        #     "has_active_branch_weight",
        #     "is_open_weight",
        #     Coalesce("position", Value(999999)),
        #     "distance"
        # )

        return queryset.order_by(
            "has_active_branch_weight",
            "is_open_weight",
            Coalesce("position", Value(999999)),
            "distance"
        )


class ShopViewSet(InstitutionViewSet):
    def get_queryset(self):
        return super(ShopViewSet, self).get_queryset().filter(type="shop")


class LikeInstitutionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        institution_id = pk
        user = request.user

        try:
            LikedInstitutions.objects.get(customer=user, institution_id=institution_id).delete()
            response = {"action": "dislike"}

        except LikedInstitutions.DoesNotExist:
            obj = LikedInstitutions(customer=user, institution_id=institution_id)
            obj.save()
            response = {"action": "like"}

        return Response(data=response)


class LikedInstitutionsList(InstitutionViewSet):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = super(LikedInstitutionsList, self).get_queryset().filter(type="restaurant").filter(id__in=user.liked_institutions.values_list("institution_id", flat=True))

        # queryset = (
        #     Institution.objects.get_available()
        #     .with_is_open_by_schedule()
        #     .filter(id__in=user.liked_institutions.values_list("institution_id", flat=True))
        #     .select_related("category")
        #     .prefetch_related(Prefetch("branches", InstitutionBranch.objects.select_related("address").with_is_open_by_schedule()))
        #     .annotate(
        #         rating=Avg("feedback_rates__value"),
        #         has_active_branch=Case(
        #             When(
        #                 is_open=True,  # institution.is_open
        #                 then=Exists(
        #                     InstitutionBranch.objects.get_available().filter(
        #                         institution=OuterRef("pk"), is_open=True, is_active=True
        #                     )
        #                 ),
        #             ),
        #             default=Value(False),
        #             output_field=BooleanField(),
        #         ),
        #         is_open_by_schedule=Case(
        #             When(
        #                 is_open=True,
        #                 then=Exists(
        #                     InstitutionBranch.objects.with_is_open_by_schedule().filter(
        #                         institution=OuterRef("pk"), is_open_by_schedule=True
        #                     )
        #                 ),
        #             ),
        #             default=Value(False),
        #             output_field=BooleanField(),
        #         )
        #     )
        # ).filter(
        #     branches__region_branch__polygon__contains=Point((float(self.request.query_params.get("lat", 0)), float(self.request.query_params.get("long", 0)))),
        #     branches__is_open_by_schedule=True,
        #     branches__is_open=True,
        #     branches__is_active=True
        # )
        return Response(
            InstitutionListSerializer(queryset, many=True, context={"request": request}).data
        )


class RateInstitutionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        institution_id = pk
        rating_value = request.data.get("rating")
        try:
            rating = InstitutionRating.objects.get(
                customer=request.user, institution_id=institution_id
            )
        except InstitutionRating.DoesNotExist:
            rating = InstitutionRating(customer=request.user, institution_id=institution_id)
        rating.rating = rating_value
        rating.save()
        response = {"action": "rate"}
        return Response(response)


class SearchView(views.APIView):
    def get(self, request, pk):
        try:
            institution = Institution.objects.get_available().select_related("category").annotate(rating=Round(Avg("feedback_rates__value"), 2))
        except InstitutionRating.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        search_text = request.query_params.get("search")
        products = Product.objects.filter(
            Q(status="active"),
            Q(name_uz__icontains=search_text)
            | Q(name_ru__icontains=search_text)
            | Q(name_en__icontains=search_text),
            Q(category__institution=institution),
        )
        serializer = ProductListSerializer(products, many=True, context={"request": request})
        return Response(serializer.data)
class ImportView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get_cred(self, institution):
        return {
            "endpoint_url": institution.endpoint_url,
            "client_id": institution.client_id,
            "client_secret": institution.client_secret
        }
    
    def do_import(self, id):
        institution = Institution.objects.get(pk=id)

        rkeeper = rkeeperAPI(endpoint_url=institution.endpoint_url, client_id=institution.client_id, client_secret=institution.client_secret)
        
        restaurants = rkeeper.get_restaurants()
        
        # logging.basicConfig()

        for rest in restaurants['places']:
            seed_institution_branch(institution, rest)
            menu = rkeeper.get_menu(rest['id'])
            
            # print(f"Branch: {rest['id']} | Kategoriya: {len(menu['categories'])} | Produkt: {len(menu['items'])}")

            for cat in menu['categories']:
                seed_category(institution, cat)
            for item in menu['items']:
                seed_products(institution, rest['id'], item)
                
    def get(self, request, pk):
        threading.Thread(target=self.do_import, args=(pk,)).start()
        return Response({
            "status": "accepted",
            "message": "Import jarayoni boshlandi."
        })
    
    def post(self, request, pk):
        institution = Institution.objects.get(pk=pk)
        data = request.data
        institution.client_id = data.get("client_id")
        institution.client_secret = data.get("client_secret")
        institution.endpoint_url = data.get("endpoint_url", "https://rkeeper.api.deliveryhub.uz")
        institution.save()

        threading.Thread(target=self.do_import, args=(pk,)).start()
        return Response({
            "status": "accepted",
            "message": "Import jarayoni boshlandi."
        })
