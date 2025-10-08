from rest_framework import serializers

from order.feedback.models import InstitutionFeedback, DeliveryFeedback


class InstitutionFeedbackSerializer(serializers.ModelSerializer):
    
    institution = serializers.SerializerMethodField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = InstitutionFeedback
        fields = ["order", "value", "comment", "institution", "user", "created"]

        extra_kwargs = {
            "comment": {"required": False, "allow_blank": True},
        }

    def get_user(self, obj):
        customer = obj.order.customer
        if customer:
            return {"id": customer.id, "first_name": customer.first_name, "last_name": customer.last_name, "phone": customer.phone_number}
        return {}

    def get_institution(self, obj):
        institution = obj.order.item_groups.first()
        if institution:
            return {"id": institution.institution.id, "name": str(institution.institution), "branch": str(institution.institution_branch)}
        return {}



class DeliveryFeedbackSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)
    courier = serializers.SerializerMethodField(read_only=True)
    institution = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DeliveryFeedback
        fields = ["order", "value", "comment", "courier", "user", "institution", "created"]
        extra_kwargs = {
            "comment": {"required": False, "allow_blank": True},
        }

    def get_user(self, obj):
        customer = obj.order.customer
        if customer:
            return {"id": customer.id, "first_name": customer.first_name, "last_name": customer.last_name, "phone": customer.phone_number}
        return {}

    def get_institution(self, obj):
        institution = obj.order.item_groups.first()
        if institution:
            return {"id": institution.institution.id, "name": str(institution.institution), "branch": str(institution.institution_branch)}
        return {}

    def get_courier(self, obj):
        courier = obj.courier
        if courier:
            return {"id": courier.id, "first_name": courier.user.first_name, "last_name": courier.user.last_name, "phone": courier.user.phone_number}
        return {}

