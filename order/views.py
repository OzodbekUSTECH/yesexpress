from django.db.models import Count, Exists, OuterRef
from order.feedback.models import DeliveryFeedback, InstitutionFeedback
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Order
from .serializers import OrderSerializer
from .services import OrderService
from .status_controller import cancel_order

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    queryset = (
        Order.objects.sorted_by_condition()
        .prefetch_related(
            "item_groups__items__options",
            "item_groups__institution",
            "item_groups__institution__address",
            "item_groups__items__product",
            "payment_set__ofd_receipts",
        )
        .select_related("customer", "address", "courier")
        .exclude(status="pending")
    )
    serializer_class = OrderSerializer


    @action(detail=False, methods=['get'], url_path='review')
    def get_no_comments(self, request):
        user = self.request.user
        queryset = super(OrderViewSet, self).get_queryset()
        queryset = queryset.annotate(group_count=Count("item_groups")).filter(
            group_count__gte=1, customer=user
        ).annotate(
            has_inst_feedback=Exists(InstitutionFeedback.objects.filter(order=OuterRef('pk'))),
            has_del_feedback=Exists(DeliveryFeedback.objects.filter(order=OuterRef('pk')))
        ).filter(
            has_inst_feedback=False,
            has_del_feedback=False
        ).filter(status="closed").order_by("-id")
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


    def get_queryset(self):
        user = self.request.user
        if self.request.query_params.get("all"):
            return super(OrderViewSet, self).get_queryset()
        queryset = super(OrderViewSet, self).get_queryset()
        queryset = queryset.annotate(group_count=Count("item_groups")).filter(
            group_count__gte=1, customer=user
        ).order_by("-id")
        return queryset

    def create(self, request, *args, **kwargs):
        serializer_instance = self.serializer_class(data=request.data, context={"request": request})

        if not serializer_instance.is_valid():
            return Response(serializer_instance.errors, status=400)

        order_service = OrderService(serializer_instance=serializer_instance, customer=request.user)
        try:
            order = order_service.create()
            return Response({"id": order.id}, status=201)
        except Exception as e:
            return Response(
            {
                "status":"error", 
                "message": {
                    "uz": "Hozirda ushbu tashkilot yopiq, iltimos tashkilot ochilgandan so'ng qayta urinib ko'ring.",
                    "ru": "В настоящее время организация закрыта, пожалуйста, попробуйте снова, когда она будет открыта.",
                    "en": "The organization is currently closed, please try again once it reopens."
                }
            }, 
            status=400)

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()

        if order.status == 'rejected':
            return Response(data={"status": "success"})

        is_success, message = cancel_order(order)

        if is_success:
            return Response(data={"status": "success"})

        return Response(data={"status": "error", "message": message}, status=400)
