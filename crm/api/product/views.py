from django.db.models import Prefetch, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from base.api_views import MultiSerializerViewSetMixin, DynamicPagination
from crm.api.product.serializers import (
    CrmProductSerializer,
    CrmProductCategorySerializer,
    CrmProductOptionSerializer,
    CrmProductOptionCreateSerializer,
    CrmOptionItemSerializer,
    CrmOptionItemUpdateSerializer,
    CrmProductOptionUpdateSerializer,
    CrmProductDetailSerializer,
    CrmProductCreateSerializer,
)
from product.models import Product, ProductCategory, ProductOption, OptionItem, ProductToBranch
from .permissions import ProductPermission


class CategoryViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = ProductCategory.objects.filter(is_deleted=False).order_by("name", "institution")
    serializer_action_classes = {
        "list": CrmProductCategorySerializer,
        "retrieve": CrmProductCategorySerializer,
        "create": CrmProductCategorySerializer,
        "partial_update": CrmProductCategorySerializer,
    }
    pagination_class = DynamicPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ["name_ru", "name_uz", "name_en"]
    filterset_fields = ["institution"]
    permission_classes = [IsAuthenticated, ProductPermission]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("institution")
            .filter(institution__is_deleted=False)
            .order_by("position")
        )
        if self.request.user.type in ["institution_admin", "institution_owner"]:
            institution = self.request.user.get_institution()
            if institution:
                qs = qs.filter(institution=institution)
            else:
                qs = qs.none()

        return qs

    def list(self, request, *args, **kwargs):
        if self.request.user.get_institution():
            if isinstance(self.request.user.get_institution(), int):
                self.branches_id = self.request.user.get_institution()
            else:
                self.branches_id = list(self.request.user.get_institution().branches.values_list("id", flat=True))
        return super().list(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["branches_id"] = getattr(self, "branches_id", None)
        return context
    
    def destroy(self, request, *args, **kwargs):
        category: ProductCategory = self.get_object()
        category.is_deleted = True
        category.save()
        category.product_set.update(is_deleted=True)
        return Response(status=204)


class ProductViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Product.objects.select_related("category__institution")
    serializer_action_classes = {
        "list": CrmProductSerializer,
        "retrieve": CrmProductDetailSerializer,
        "create": CrmProductCreateSerializer,
        "partial_update": CrmProductCreateSerializer,
    }
    pagination_class = DynamicPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ["institution", "category", "status"]
    search_fields = ["name_ru", "name_uz", "name_en"]
    permission_classes = [IsAuthenticated, ProductPermission]

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False, institution__is_deleted=False)
        
        user = self.request.user
        user_type = user.type
       
        branch_filter =  Q(institution_branches__institution__owner=self.request.user) | Q(institution_branches__institution__admin=self.request.user) | Q(institution_branches__workers__worker=self.request.user)
        
        if user.is_superuser or user.type in ['main_admin', 'admin']:
            institution = self.request.query_params.get('institution')
            if institution:
                branch_filter = Q(institution_branches__institution=int(institution))
        
        # print(branch_filter)
        
        qs = qs.prefetch_related(
            Prefetch(
                "options",
                ProductOption.objects.get_not_deleted().prefetch_related(
                    Prefetch("items", OptionItem.objects.filter(is_deleted=False))
                ),
            ),
            Prefetch("branches", ProductToBranch.objects.select_related("institution_branches").filter(branch_filter).distinct())
        )
        
        if user_type in ["institution_admin", "institution_owner"]:
            institution = user.get_institution()
            if institution:
                qs = qs.filter(institution=institution)
            else:
                qs = qs.none()
        return qs.order_by("name", "institution")

    def partial_update(self, request, pk, *args, **kwargs):
        data = request.data
        product = Product.objects.get(pk=pk)
        if isinstance(data, list):
            for row in data:
                product_to_branch, created = ProductToBranch.objects.get_or_create(
                    product=product,
                    institution_branches_id=row['id'],
                    defaults={'is_available': row['status']}
                )
                if not created:
                    product_to_branch.is_available = row['status'] 
                    product_to_branch.save()

            serializer = self.get_serializer(product)
            return Response(serializer.data)

        
        serializer = self.get_serializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
        
            institution_branches = request.query_params.get('institution_branches')
            if institution_branches:
                
                product_to_branch, created = ProductToBranch.objects.get_or_create(
                    product=product,
                    institution_branches_id=institution_branches,
                    defaults={'is_available': request.data['is_available']}
                )
                if not created:
                    product_to_branch.is_available = request.data['is_available']
                    product_to_branch.save()

            return Response(serializer.data)

        return Response(serializer.errors, status=400)

    def list(self, request, *args, **kwargs):
        if self.request.user.get_institution():
            if isinstance(self.request.user.get_institution(), int):
                self.branches_id = self.request.user.get_institution()
            else:
                self.branches_id = list(self.request.user.get_institution().branches.values_list("id", flat=True))
        return super().list(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["branches_id"] = getattr(self, "branches_id", None)
        return context

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        product.is_deleted = True
        product.save()
        return Response(status=204)


class ProductOptionViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = ProductOption.objects.get_not_deleted().prefetch_related("items")
    serializer_action_classes = {
        "list": CrmProductOptionSerializer,
        "retrieve": CrmProductOptionSerializer,
        "create": CrmProductOptionCreateSerializer,
        "partial_update": CrmProductOptionUpdateSerializer,
    }
    permission_classes = [IsAuthenticated, ProductPermission]
    pagination_class = DynamicPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ["product"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.is_deleted = True
        instance.deleted_user = request.user
        instance.deleted_at = timezone.now()
        instance.save()
        return Response(status=204)


class ProductOptionItemViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = OptionItem.objects.filter(is_deleted=False)
    serializer_action_classes = {
        "list": CrmOptionItemSerializer,
        "retrieve": CrmOptionItemSerializer,
        "create": CrmOptionItemUpdateSerializer,
        "partial_update": CrmOptionItemUpdateSerializer,
    }
    permission_classes = [IsAuthenticated, ProductPermission]
    pagination_class = DynamicPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ["option"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.deleted_user = request.user
        instance.deleted_at = timezone.now()
        instance.save()
        return Response(status=204)
