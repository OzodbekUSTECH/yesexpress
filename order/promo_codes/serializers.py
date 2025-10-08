from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from order.promo_codes.models import PromoCode, PromoCodeUsage


class PromoCodeNotUsedByUserValidator:
    requires_context = True

    def __call__(self, value, serializer):
        if request := serializer.context.get("request"):
            user_id = request.user.id
            if PromoCodeUsage.objects.filter(user_id=user_id, promo_code=value).exists():
                raise ValidationError({
                    "status": "error",
                    "message": {
                        "uz": "Siz ushbu koddan foydalangansiz.",
                        "ru": "Вы уже использовали этот код.",
                        "en": "You have already used this code."
                    }
                })


class PromoCodeInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = [
            "name",
            "description",
            "sum", "code",
            "min_order_sum",
            "start_date",
            "end_date"
        ]


class GetPromoCodeInfoSerializer(serializers.Serializer):
    promo_code = serializers.SlugRelatedField(
        queryset=PromoCode.objects.filter_usable(),
        slug_field="code",
        validators=[PromoCodeNotUsedByUserValidator()],
    )
