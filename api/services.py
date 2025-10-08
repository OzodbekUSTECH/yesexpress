from django.db.models import Q, Avg, Prefetch, Exists, OuterRef, Case, Value, When, BooleanField
from django.db.models.functions import Round
from django.contrib.gis.geos import Point

from institution.models import Institution, InstitutionBranch
from product.models import Product
from institution.serializers import InstitutionSearchSerializer

def search_results(search_text, request):
    
    if search_text is None:
        return []
    
    products_qs = Product.objects.filter(Q(name_uz__icontains=search_text) |
            Q(name_ru__icontains=search_text) |
            Q(name_en__icontains=search_text), status='active', is_deleted=False).values_list('institution_id', flat=True)


    institutions = Institution.objects\
        .get_available()\
        .with_is_open_by_schedule()\
        .select_related("category")\
        .annotate(
            rating=Round(Avg("feedback_rates__value"), 2),
            has_active_branch=Case(
                When(
                    is_open=True,  # institution.is_open
                    then=Exists(InstitutionBranch.objects.get_available().filter(institution=OuterRef("pk"), is_open=True, is_active=True)),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
            is_open_by_schedule=Case(
                When(
                    is_open=True,
                    then=Exists(
                        InstitutionBranch.objects.with_is_open_by_schedule().filter(
                            institution=OuterRef("pk"), is_open_by_schedule=True
                        )
                    ),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )
        ).filter(is_open_by_schedule=True, is_open=True, has_active_branch=True).filter(
            Q(name__icontains=search_text) |
            Q(id__in=products_qs) 
        )\
        .prefetch_related(Prefetch(
        "product_set",
        queryset=Product.objects.filter(Q(name_uz__icontains=search_text) |
            Q(name_ru__icontains=search_text) |
            Q(name_en__icontains=search_text), status='active', is_deleted=False, branches__is_available=True),
    )).distinct()


    serializer = InstitutionSearchSerializer(
        institutions, many=True, context={
            "request": request,
            "lat": request.query_params.get("lat"),
            "long": request.query_params.get("long")
        }
    )
    return serializer.data
