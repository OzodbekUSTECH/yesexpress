from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from base.api_views import MultiSerializerViewSetMixin, DynamicPagination
from base.helpers import set_obj_deleted
from courier.models import InstitutionDeliverySettings
from crm.api.institution.serializers import (
    CrmInstitutionSerializer,
    CrmInstitutionCreateSerializer,
    CrmInstitutionCategorySerializer,
    CrmInstitutionDetailSerializer,
    CrmInstitutionDeliverySettingsSerializer,
    CrmInstitutionBranchSerializer,
    CrmInstitutionBranchScheduleUpdate,
    CrmInstitutionBranchDetailSerializer,
    CrmInstitutionBranchCreateSerializer,
    CrmInstitutionBranchScheduleSerializer,
)
from crm.api.institution.services import (
    handle_institution_delete,
    create_or_update_institution_schedule_days,
)
from crm.api.user.serializers import (
    CrmInstitutionUserSerializer,
    CrmInstitutionUpdateSerializer,
    CrmInstitutionChangePasswordSerializer,
)
from institution.models import (
    Institution,
    InstitutionCategory,
    InstitutionBranch,
    InstitutionBranchSchedule,
)
from user.services import handle_user_delete
from .permissions import InstitutionPermission


class InstitutionCategoryViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = InstitutionCategory.objects.get_available()
    serializer_action_classes = {
        "list": CrmInstitutionCategorySerializer,
        "retrieve": CrmInstitutionCategorySerializer,
        "create": CrmInstitutionCategorySerializer,
        "partial_update": CrmInstitutionCategorySerializer,
    }
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]
    pagination_class = DynamicPagination
    search_fields = ["title"]
    permission_classes = [IsAuthenticated, InstitutionPermission]

    def destroy(self, request, *args, **kwargs):
        instance: InstitutionCategory = self.get_object()
        instance.institution_set.update(
            is_active=False, is_deleted=True, deleted_at=timezone.now(), deleted_user=request.user
        )
        set_obj_deleted(instance, request.user)
        return Response(status=204)


class InstitutionViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Institution.objects.get_not_deleted()
    serializer_action_classes = {
        "list": CrmInstitutionSerializer,
        "retrieve": CrmInstitutionDetailSerializer,
        "create": CrmInstitutionCreateSerializer,
        "partial_update": CrmInstitutionCreateSerializer,
        "add_institution_admin": CrmInstitutionUserSerializer,
        "update_institution_admin": CrmInstitutionUpdateSerializer,
        "change_institution_admin_password": CrmInstitutionChangePasswordSerializer,
        "add_institution_owner": CrmInstitutionUserSerializer,
        "update_institution_owner": CrmInstitutionUpdateSerializer,
        "change_institution_owner_password": CrmInstitutionChangePasswordSerializer,
        "get_delivery_settings": CrmInstitutionDeliverySettingsSerializer,
        "update_delivery_settings": CrmInstitutionDeliverySettingsSerializer,
    }
    permission_classes = [IsAuthenticated, InstitutionPermission]
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]
    pagination_class = DynamicPagination
    filterset_fields = ["category", "type", "delivery_by_own"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.type in ["institution_admin", "institution_owner", "institution_worker"]:
            qs = qs.filter(Q(admin=user) | Q(owner=user) | Q(branches__workers__worker__id=user.id)).distinct()

        if self.action in ["retrieve"]:
            qs = qs.select_related("address", "category", "owner", "admin").prefetch_related(
                Prefetch("branches", InstitutionBranch.objects.select_related("address"))
            )
        return qs

    def destroy(self, request, *args, **kwargs):
        instance: Institution = self.get_object()
        handle_institution_delete(instance, request.user)
        return Response(status=204)

    def add_institution_admin(self, request, *args, **kwargs):
        institution = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            admin = serializer.save(type="institution_admin")
            institution.admin = admin
            institution.save()
        return Response(serializer.data, status=201)

    def update_institution_admin(self, request, *args, **kwargs):
        institution = self.get_object()
        if not institution.admin:
            return Response({"message": "У заведения нет администратора"}, status=400)
        serializer = self.get_serializer(
            instance=institution.admin, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def change_institution_admin_password(self, request, *args, **kwargs):
        institution = self.get_object()
        if not institution.admin:
            return Response({"message": "У заведения нет администратора"}, status=400)
        serializer = self.get_serializer(instance=institution.admin, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Пароль успешно изменен"})

    def delete_institution_admin(self, request, *args, **kwargs):
        institution = self.get_object()
        admin = institution.admin
        handle_user_delete(institution.admin)
        institution.admin = None
        admin.save()
        institution.save()
        return Response(status=204)

    def add_institution_owner(self, request, *args, **kwargs):
        institution = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            owner = serializer.save(type="institution_owner")
            institution.owner = owner
            institution.save()
        return Response(serializer.data, status=201)

    def update_institution_owner(self, request, *args, **kwargs):
        institution = self.get_object()
        if not institution.owner:
            return Response({"message": "У заведения нет владельца"}, status=400)
        serializer = self.get_serializer(
            instance=institution.owner, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def change_institution_owner_password(self, request, *args, **kwargs):
        institution = self.get_object()
        if not institution.owner:
            return Response({"message": "У заведения нет владельца"}, status=400)
        serializer = self.get_serializer(instance=institution.owner, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Пароль успешно изменен"})

    def get_delivery_settings(self, request, *args, **kwargs):
        institution: Institution = self.get_object()
        institution_delivery_settings = InstitutionDeliverySettings.objects.filter(
            institution=institution
        ).first()
        serializer = self.get_serializer(institution_delivery_settings)
        return Response(serializer.data)

    def update_delivery_settings(self, request, *args, **kwargs):
        institution: Institution = self.get_object()
        institution_delivery_settings = InstitutionDeliverySettings.objects.filter(
            institution=institution
        ).first()

        with transaction.atomic():
            if not institution_delivery_settings:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save(institution=institution)
            else:
                serializer = self.get_serializer(
                    instance=institution_delivery_settings, data=request.data
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
        return Response(serializer.data)


class InstitutionBranchViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, InstitutionPermission]
    queryset = InstitutionBranch.objects.get_not_deleted().select_related("address")
    serializer_action_classes = {
        "list": CrmInstitutionBranchSerializer,
        "retrieve": CrmInstitutionBranchDetailSerializer,
        "create": CrmInstitutionBranchCreateSerializer,
        "partial_update": CrmInstitutionBranchCreateSerializer,
        "update_schedule": CrmInstitutionBranchScheduleUpdate,
    }
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]
    pagination_class = DynamicPagination
    filterset_fields = ["institution"]
    search_fields = ["name"]

    @swagger_auto_schema(responses={200: CrmInstitutionBranchScheduleSerializer()})
    def update_schedule(self, request, *args, **kwargs):
        institution_branch = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        create_or_update_institution_schedule_days(
            institution_branch,
            days_of_week=validated_data["days_of_week"],
            start_time=validated_data["start_time"],
            end_time=validated_data["end_time"],
        )
        schedule_days = InstitutionBranchSchedule.objects.filter(institution=institution_branch)
        return Response(CrmInstitutionBranchScheduleSerializer(schedule_days, many=True).data)

    @swagger_auto_schema(responses={200: CrmInstitutionBranchScheduleSerializer()})
    def change_schedule_day_active(self, request, *args, **kwargs):
        institution_schedule_day = get_object_or_404(
            InstitutionBranchSchedule,
            institution_id=kwargs["pk"],
            pk=kwargs["schedule_id"],
        )
        institution_schedule_day.is_active = not institution_schedule_day.is_active
        institution_schedule_day.save()
        return Response(CrmInstitutionBranchScheduleSerializer(institution_schedule_day).data)

import io
import pandas as pd
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from order.models import Order
from collections import defaultdict
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

class InstitutionReportAPIView(APIView):
    def get(self, request):
        try:
            # Query params
            start_time_str = request.query_params.get('start_time')
            end_time_str = request.query_params.get('end_time')
            export_type = request.query_params.get('export_type')  # xls, csv, pdf

            if start_time_str and end_time_str:
                start_time = datetime.fromisoformat(start_time_str)
                end_time = datetime.fromisoformat(end_time_str)
            else:
                now = timezone.now()
                start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_time = now

            # Orders
            orders = Order.objects.select_related(
                'customer', 'operator'
            ).prefetch_related(
                'item_groups__institution_branch__institution',
                'item_groups__items__product',
            ).filter(
                created_at__gte=start_time,
                created_at__lte=end_time,
                status__in=["closed", "shipped"]
            )

            institution_data = defaultdict(lambda: {
                "products_sum": 0,
                "nal_sum": 0,
                "payme_sum": 0,
                "nds_sum": 0,
                "institution": None
            })

            for order in orders:
                for item_group in order.item_groups.all():
                    branch = item_group.institution_branch
                    if not branch or not branch.institution:
                        continue

                    institution = branch.institution
                    key = institution.id

                    institution_data[key]["institution"] = institution
                    institution_data[key]["products_sum"] += item_group.products_sum

                    if order.payment_method == "cash":
                        institution_data[key]["nal_sum"] += item_group.products_sum
                    elif order.payment_method == "payme":
                        institution_data[key]["payme_sum"] += item_group.products_sum

                    for item in item_group.items.all():
                        if item.product and item.product.vat:
                            vat = item.product.vat / 100
                            nds_for_item = item.total_sum * vat
                            institution_data[key]["nds_sum"] += nds_for_item

            rows = []
            for key, data in institution_data.items():
                institution = data["institution"]
                products_sum = data["products_sum"]
                nal_sum = data["nal_sum"]
                payme_sum = data["payme_sum"]
                nds_sum = data["nds_sum"]

                tax_percentage = institution.tax_percentage_ordinary or 0
                доход = products_sum * (tax_percentage / 100)
                sch_fra = доход + nds_sum
                raznica = products_sum - sch_fra - nal_sum

                rows.append({
                    "Юридическое название": institution.name,
                    "Бренд": institution.legal_name,
                    "%": f"{tax_percentage}%",
                    "Реализация": round(products_sum, 2),
                    "Доход": round(доход, 2),
                    "НДС": round(nds_sum, 2),
                    "Сч-ф-ра": round(sch_fra, 2),
                    "Нал": round(nal_sum, 2),
                    "PayMe": round(payme_sum, 2),
                    "Разница": round(raznica, 2),
                })

            df = pd.DataFrame(rows)

            if export_type == "xls":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name="Institution Report")
                output.seek(0)
                filename = f"institution_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                response = HttpResponse(
                    output,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return response

            elif export_type == "csv":
                output = io.StringIO()
                df.to_csv(output, index=False)
                output.seek(0)
                filename = f"institution_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
                response = HttpResponse(
                    output,
                    content_type="text/csv"
                )
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return response
            else:
                return Response(rows, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        