from django.db import models
from django.db.models import F

from order.models import Order


class AbstractDeliverySettings(models.Model):
    """
    Глобальные настройки доставки
    """

    min_distance = models.IntegerField(verbose_name="Минимальная дистанция доставки, в километрах")
    min_delivery_price = models.IntegerField(verbose_name="Минимальная сумма доставки, в сумах")
    price_per_km = models.IntegerField(verbose_name="Цена за 1 километр, в сумах")

    class Meta:
        verbose_name = "Настройки доставки"
        verbose_name_plural = verbose_name
        abstract = True

    def __str__(self):
        return "Редактировать наcтройки"


class DeliverySettings(AbstractDeliverySettings):
    class Meta:
        verbose_name = "Глобальные настройки доставки"
        verbose_name_plural = verbose_name


class InstitutionDeliverySettings(AbstractDeliverySettings):
    """
    Настройки доставки для отдельного заведения
    """

    institution = models.OneToOneField(
        "institution.Institution",
        on_delete=models.CASCADE,
        related_name="delivery_settings",
        verbose_name="Заведение",
    )

    class Meta:
        verbose_name = "Настройки доставки для отдельного заведения"
        verbose_name_plural = "Настройки доставки для отдельного заведения"

    def __str__(self):
        return f"{self.institution.name}"


class Courier(models.Model):
    class Transport(models.TextChoices):
        CAR = "car", "машина"
        SCOOTER = "scooter", "скутер"
        BICYCLE = "bicycle", "велосипед"
        FOOT = "foot", "пешком"

    class Status(models.TextChoices):
        FREE = "free", "свободный"
        IN_INSTITUTION = "in_institution", "в заведении"
        DELIVERING = "delivering", "на доставке"
        INACTIVE = "inactive", "неактивный"

    user = models.OneToOneField("user.User", on_delete=models.CASCADE, related_name="courier")
    passport_series = models.CharField(verbose_name="Серия паспорта", max_length=255)
    transport = models.CharField(
        verbose_name="Вид транспорта", max_length=255, choices=Transport.choices
    )
    car_info = models.CharField(max_length=50, null=True, blank=True, verbose_name="Марка машины")
    registration_number = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Регистрационный номер машины"
    )
    thermal_bag_number = models.IntegerField(null=True, blank=True, verbose_name="Номер термосумки")
    balance = models.IntegerField(verbose_name="Баланс курьера", default=0)
    status = models.CharField(
        verbose_name="Статус курьера",
        default=Status.INACTIVE,
        choices=Status.choices,
        max_length=255,
    )
    is_deleted = models.BooleanField(default=False, verbose_name="Удален")
    # is_active = models.BooleanField(default=True, blank=True, null=True)
    class Meta:
        verbose_name = "Курьер"
        verbose_name_plural = "Курьеры"

    def update_balance(self, amount, type):
        if type == 'in':
            Courier.objects.filter(id=self.id).update(balance=F('balance') + amount)
        elif type == 'out':
            Courier.objects.filter(id=self.id).update(balance=F('balance') - amount)

    def __str__(self):
        return self.user.phone_number


class Transaction(models.Model):
    courier = models.ForeignKey(Courier, verbose_name="Курьер", on_delete=models.CASCADE)
    order = models.ForeignKey(Order, verbose_name="Заказ", on_delete=models.CASCADE, null=True, blank=True)
    amount = models.IntegerField(verbose_name="Сумма")
    type = models.CharField(blank=True, null=True)
    name = models.CharField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"

    @staticmethod
    def create_with_balance(courier, order, amount, type, name):
        courier.update_balance(amount, type)
        return Transaction.objects.create(
            courier=courier,
            order=order,
            amount=amount,
            type=type,
            name=name
        )
    
    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.courier} {self.amount}"
