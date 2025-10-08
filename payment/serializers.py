from rest_framework import serializers

from payment.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    receipt_url = serializers.SerializerMethodField(allow_null=True, read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "payment_type", "payment_method", "amount", "receipt_url", "order"]

    def get_receipt_url(self, obj: Payment):
        receipt = obj.ofd_receipts.first()
        if receipt:
            return receipt.qr_code_url
        return None
