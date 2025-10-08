import os

import django

from dotenv import load_dotenv


load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tuktuk.settings")
django.setup()

from payment.models import Payment
from ofd.services import OFDReceiptService


def main():
    payment = Payment.objects.get(id=13)
    ofd_s = OFDReceiptService(payment)
    # ofd_s.create_prepayment_receipt()
    ofd_s.create_credit_receipt()
    # sale_receipt = OFDReceipt.objects.get(id=48)
    # ofd_s.create_refund_receipt(sale_receipt)


if __name__ == "__main__":
    main()
