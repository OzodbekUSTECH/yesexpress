from rest_framework import serializers

from order.promo_codes.models import PromoCode
from user.models import User


class CrmPromoCodeSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True).all(), many=True, required=False, write_only=True
    )
    users_id = serializers.SerializerMethodField()
    class Meta:
        model = PromoCode
        fields = (
            "id",
            "name",
            "description",
            "sum",
            "code",
            "users",
            "users_id",
            "revokable",
            "min_order_sum",
            "start_date",
            "end_date"
        )

    def get_users_id(self, obj):
        return [{"id": u.id, "phone_number": u.phone_number} for u in obj.users.all()]