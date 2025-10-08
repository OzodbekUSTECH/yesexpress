from django.db import models

from base.models import TimeStampedFlagsModel
from order.models import PAYMENT_METHODS


class Payment(TimeStampedFlagsModel):
    PAYMENT_TYPE = (("INCOME", "Приход"), ("OUTCOME", "Расход"))

    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE, verbose_name="Тип платежа")
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHODS,
        verbose_name="Метод оплаты",
    )
    order = models.ForeignKey(
        "order.Order", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Заказ"
    )
    amount = models.IntegerField(default=0, verbose_name="Сумма")
    receipt_required = models.BooleanField(default=False, verbose_name="Необходима фискализация")

    def __str__(self):
        return f"Платеж №{self.id}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
