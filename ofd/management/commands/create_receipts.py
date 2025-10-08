from django.core.management.base import BaseCommand

from ofd.services import OFDReceiptService
from payment.models import Payment


class Command(BaseCommand):
    help = "Create receipts"

    def handle(self, *args, **options):
        payments = Payment.objects.get_available().filter(
            receipt_required=True, ofd_receipts__isnull=True
        )
        for payment in payments:
            ofd_service = OFDReceiptService(payment)
            try:
                ofd_service.create_sale_receipt()
            except Exception:
                pass
