from rest_framework import serializers

from .models import PaymeCard

from order.models import Order


class PaymentSerializer(serializers.Serializer):
    card = serializers.PrimaryKeyRelatedField(queryset=PaymeCard.objects.all())
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        fields = ["card", "order"]


class CardSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PaymeCard
        fields = ["id", "token", "expires", "hidden_number", "owner", "name"]

class ShortCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymeCard
        fields = ["id", "expires", "hidden_number", "name"]
