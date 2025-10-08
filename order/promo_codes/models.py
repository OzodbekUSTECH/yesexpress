from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import QuerySet, Case, When
from django.db.models.functions import Now


class PromoCode(models.Model):
    class Queryset(QuerySet):
        def annotate_usable(self):
            now = Now()
            return self.annotate(
                usable=Case(
                    When(start_date__lte=now, end_date__gte=now, is_active=True, then=True),
                    default=False,
                    output_field=models.BooleanField(),
                )
            )

        def filter_usable(self):
            return self.annotate_usable().filter(usable=True)
        
    users = models.ManyToManyField("user.User",  related_name="used_promo_codes")
    name = models.CharField(verbose_name="Название", max_length=64, default="Промокод")
    status = models.CharField(verbose_name="Статус", max_length=64, default="active")
    description = models.TextField(verbose_name="Описание", max_length=512, blank=True, default="")
    sum = models.IntegerField(verbose_name="Сумма", default=15_000)
    code = models.CharField(verbose_name="Код активации", max_length=156, unique=True)
    revokable = models.BooleanField(
        default=False,
        verbose_name="Деактивировать после использования (только для одного пользователя)",
    )
    min_order_sum = models.IntegerField(default=30_000, verbose_name="Минимальная сумма заказа")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    is_active = models.BooleanField(default=True, verbose_name="Активность")

    start_date = models.DateTimeField(verbose_name="Дата начала")
    end_date = models.DateTimeField(verbose_name="Дата окончания")

    objects = Queryset.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"


class PromoCodeUsage(models.Model):
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, verbose_name="Пользователь"
    )
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, verbose_name="Промокод")
    order = models.OneToOneField("order.Order", on_delete=models.CASCADE, verbose_name="Заказ")
    used_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время использования")

    def __str__(self):
        return f"{self.promo_code} by {self.user}"

    class Meta:
        ordering = ["-used_at"]
        unique_together = ["user", "promo_code"]
        verbose_name = "Использование промокода"
        verbose_name_plural = "Использование промокодов"
