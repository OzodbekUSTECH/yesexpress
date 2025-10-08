import uuid

from django.db import models, transaction


def get_certificate_upload_to(instance, filename):
    return f"certs/user-etp{instance.version}.crt"


class OFDCertificate(models.Model):
    certificate_file = models.FileField(
        upload_to=get_certificate_upload_to, verbose_name="Файл сертификата"
    )
    version = models.IntegerField(blank=True, verbose_name="Версия сертификата")
    expiration_date = models.DateField(verbose_name="Дата истечения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"ОФД Сертификат №{self.id}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            last_cert = OFDCertificate.objects.select_for_update().order_by("-version").first()
            self.version = (last_cert.version + 1) if last_cert else 1

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-version", "-created_at"]
        verbose_name = "Сертификат ОФД"
        verbose_name_plural = "Сертификаты ОФД"

    @property
    def certificate_path(self):
        return self.certificate_file.path

    @classmethod
    def get_active_certificate(cls):
        return cls.objects.order_by("-version", "created_at").first()


class OFDReceipt(models.Model):
    class ReceiptTypes(models.TextChoices):
        SALE = "SALE", "Продажа"
        REFUND = "REFUND", "Возврат"
        CREDIT = "CREDIT", "Кредит"
        PREPAYMENT = "PREPAYMENT", "Аванс"

    terminal_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="ID терминала"
    )
    receipt_type = models.CharField(
        max_length=50, choices=ReceiptTypes.choices, verbose_name="Тип чека"
    )
    receipt_seq = models.IntegerField(null=True, blank=True, verbose_name="Номер чека")
    fiscal_sign = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Фискальный признак"
    )
    receipt_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата и время чека")
    qr_code_url = models.CharField(null=True, blank=True, verbose_name="Ссылка на QR-код")
    payment = models.ForeignKey(
        "payment.Payment",
        on_delete=models.SET_NULL,
        null=True,
        related_name="ofd_receipts",
        verbose_name="Платеж",
    )
    certificate = models.ForeignKey(
        "ofd.OFDCertificate",
        on_delete=models.PROTECT,
        null=True,
        related_name="receipts",
        verbose_name="Сертификат",
    )
    refund_receipt = models.OneToOneField(
        "ofd.OFDReceipt",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refunded_receipt",
        verbose_name="Чек возврата",
    )
    advance_contract_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        blank=True,
        null=True,
        verbose_name="Идентификатор авансового контракта",
    )

    def __str__(self):
        return f"ОФД чек №{self.receipt_seq}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.pk:
                certificate = (
                    self.certificate
                    if self.certificate
                    else OFDCertificate.get_active_certificate()
                )
                last_receipt = (
                    OFDReceipt.objects.filter(certificate=certificate)
                    .select_for_update()
                    .order_by("-receipt_seq")
                    .first()
                )
                self.receipt_seq = (last_receipt.receipt_seq + 1) if last_receipt else 1

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-receipt_seq"]
        verbose_name = "Чек ОФД"
        verbose_name_plural = "Чеки ОФД"
