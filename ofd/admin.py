from django.contrib import admin

from ofd.models import OFDReceipt, OFDCertificate


@admin.register(OFDCertificate)
class OFDCertificateAdmin(admin.ModelAdmin):
    pass


@admin.register(OFDReceipt)
class OFDReceiptAdmin(admin.ModelAdmin):
    pass
