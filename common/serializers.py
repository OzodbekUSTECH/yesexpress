from rest_framework import serializers
from .models import Settings


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = [
            "cash_payment_avaible",
        ]
