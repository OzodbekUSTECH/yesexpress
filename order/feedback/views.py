from rest_framework.generics import CreateAPIView

from order.feedback.models import InstitutionFeedback, DeliveryFeedback
from order.feedback.serializers import InstitutionFeedbackSerializer, DeliveryFeedbackSerializer


class InstitutionFeedbackAPIView(CreateAPIView):
    queryset = InstitutionFeedback
    serializer_class = InstitutionFeedbackSerializer

    def perform_create(self, serializer):
        serializer.save(
            institution=serializer.validated_data["order"].item_groups.first().institution
        )
        return super(InstitutionFeedbackAPIView, self).perform_create(serializer)


class DeliveryFeedbackAPIView(CreateAPIView):
    queryset = DeliveryFeedback
    serializer_class = DeliveryFeedbackSerializer

    def perform_create(self, serializer):
        if courier := serializer.validated_data["order"].courier:
            serializer.save(courier=courier)
        return super().perform_create(serializer)
