from django.db import models


class AbstractFeedback(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey("order.Order", on_delete=models.CASCADE, verbose_name="Заказ")
    comment = models.CharField(max_length=255, verbose_name="Комментарий", null=True, blank=True)
    value = models.PositiveSmallIntegerField(verbose_name="Значение")

    class Meta:
        abstract = True


class InstitutionFeedback(AbstractFeedback):
    institution = models.ForeignKey(
        "institution.Institution", verbose_name="Заведение", on_delete=models.CASCADE, related_name="feedback_rates"
    )

    class Meta:
        verbose_name = "Отзыв на заведение"
        verbose_name_plural = "Отзывы на заведение"

    def __str__(self):
        return f"{self.order.customer} | {self.institution} | {self.value}"


class DeliveryFeedback(AbstractFeedback):
    courier = models.ForeignKey(
        "courier.Courier", on_delete=models.CASCADE, verbose_name="Курьер", null=True, blank=True
    )

    class Meta:
        verbose_name = "Отзыв на доставку"
        verbose_name_plural = "Отзывы на доставку"

    def __str__(self):
        return f"{self.order.customer} | {self.courier} | {self.value}"
