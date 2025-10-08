from django.db import models, ProgrammingError
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.


class Settings(models.Model):
    cash_payment_avaible = models.BooleanField(
        default=False, verbose_name="Доступна ли наличная оплата"
    )
    payme_payment_avaible = models.BooleanField(
        default=False, verbose_name="Доступна ли оплата через Payme"
    )

    @classmethod
    def load(cls):
        try:
            if not cls.objects.exists():
                return cls.objects.create()
            return cls.objects.first()
        except ProgrammingError:
            return None

    common_percentage_ordinary = models.IntegerField(
        verbose_name="Процент с заказов обычный в настройках",
        default=10,
        validators=[MaxValueValidator(100), MinValueValidator(0)],
    )
    common_percentage_restaurant_couriers = models.IntegerField(
        verbose_name="Процент с заказов если курьеры самого ресторана в настройках",
        default=0,
        validators=[MaxValueValidator(100), MinValueValidator(0)],
    )
    common_percentage_self_pickup = models.IntegerField(
        verbose_name="Процент с заказов если самовывоз в настройках",
        default=0,
        validators=[MaxValueValidator(100), MinValueValidator(0)],
    )
    delivery_service_vat_percent = models.IntegerField(
        verbose_name="Процент НДС услуги по доставке",
        default=0,
        validators=[MaxValueValidator(100), MinValueValidator(0)],
    )
