from django.db import models
from fcm_django.models import FCMDevice
from .managers import OrderManager


PAYMENT_METHODS = (
    ("cash", "наличными"),
    ("payme", "payme"),
    ("terminal", "терминал"),
)


class ORDER_STATUS(models.TextChoices):
    PREORDER = "pre-order", "пред-заказ"
    CREATED = "created", "создан"
    PENDING = "pending", "ожидает оплаты"
    ACCEPTED = "accepted", "принят"
    COOKING = "cooking", "готовится"
    REJECTED = "rejected", "отменен"
    READY = "ready", "готов"
    INCIDENT = "incident", "инцидент"
    SHIPPED = "shipped", "в пути"
    CLOSED = "closed", "закрыт"


class Order(models.Model):
    STATUSES = (
        ("pre-order", "пред-заказ"),
        ("created", "создан"),
        ("pending", "ожидает оплаты"),
        ("accepted", "принят"),
        ("cooking", "готовится"),
        ("rejected", "отменен"),
        ("ready", "готов"),
        ("shipped", "в пути"),
        ("closed", "закрыт"),
        ("incident", "инцидент"),
    )
    RKEEPER_STATUS = (
        ("NEW", "создан"),
        ("ACCEPTED_BY_RESTAURANT", "принят"),
        ("COOKING", "готовится"),
        ("CANCELLED", "отменен"),
        ("READY", "готов")
    )

    status = models.CharField(verbose_name="Статус", choices=STATUSES, max_length=255)
    address = models.ForeignKey(
        to="address.Address", on_delete=models.SET_NULL, null=True, verbose_name="Адресс доставки ?"
    )
    created_at = models.DateTimeField(verbose_name="Создано", auto_now_add=True)
    completed_at = models.DateTimeField(verbose_name="Завершено", null=True, blank=True)
    updated_at = models.DateTimeField(verbose_name="Обновлено", auto_now=True)
    note = models.CharField(
        max_length=300, verbose_name="Комментарий к заказу", blank=True, default=""
    )
    is_paid = models.BooleanField(default=False, verbose_name="Статус оплаты")
    payment_method = models.CharField(
        verbose_name="Метод оплаты", max_length=255, choices=PAYMENT_METHODS
    )
    customer = models.ForeignKey(
        "user.User", verbose_name="Заказчик", on_delete=models.SET_NULL, null=True
    )
    products_sum = models.IntegerField(verbose_name="Сумма продуктов", default=0)
    delivering_sum = models.IntegerField(verbose_name="Сумма доставки", default=0)
    total_sum = models.IntegerField(verbose_name="Общая сумма (сумма платежа)", default=0)
    courier = models.ForeignKey(
        "courier.Courier", verbose_name="Курьер", null=True, blank=True, on_delete=models.SET_NULL
    )
    receipt_id = models.CharField(max_length=512, null=True, blank=True)
    fcm_device = models.ForeignKey(FCMDevice, null=True, on_delete=models.CASCADE)
    preparing_time = models.IntegerField(null=True, blank=True, verbose_name="Время приготовления")
    discount_sum = models.IntegerField(default=0, verbose_name="Сумма скидки")
    package_amount = models.IntegerField(default=0, verbose_name="Сумма пакета")
    package_quantity = models.IntegerField(default=0, verbose_name="Кол-во пакета")
    is_process = models.BooleanField(default=False, verbose_name="Обработка заказа")
    operator = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Оператор на заказ",
        related_name="orders",
    )
    self_pickup = models.BooleanField(default=False, verbose_name="Самовывоз заказа")
    cdt = models.CharField(max_length=512, null=True, blank=True)
    uuid = models.UUIDField(blank=True, null=True)
    restaurant_status = models.CharField(choices=RKEEPER_STATUS, verbose_name="Статус Rkeeper", max_length=60, null=True, blank=True)
    objects: OrderManager = OrderManager()

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-id"]

    def __str__(self):
        return f"Заказ №{self.id} пользователя {self.customer}"

class OrderStatusTimeline(models.Model):
    order = models.OneToOneField("Order", on_delete=models.CASCADE, related_name="timeline")
    
    preparing_start_at = models.DateTimeField(verbose_name="Начало приготовления с", null=True, blank=True)
    preparing_completed_at = models.DateTimeField(verbose_name="Приготовлено в", null=True, blank=True)
    preparing_lates = models.IntegerField(verbose_name="Задержка приготовления", null=True, blank=True)
    courier_assign_at = models.DateTimeField(verbose_name="Назначен курьер с", null=True, blank=True)
    courier_arrived_at = models.DateTimeField(verbose_name="Время прибытия курьера", null=True, blank=True)
    courier_take_it_at = models.DateTimeField(verbose_name="Курьер принял в", null=True, blank=True)
    courier_lates = models.IntegerField(verbose_name="Задержка доставки", null=True, blank=True)
    delivered_at = models.DateTimeField(verbose_name="Доставлено в", null=True, blank=True)

    class Meta:
        verbose_name = "Временные отметки статусов"
        verbose_name_plural = "Временные отметки статусов"

    def __str__(self):
        return f"Таймлайн заказа №{self.order.id}"
    
class OrderItemGroup(models.Model):
    created_at = models.DateTimeField(verbose_name="Создано", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Обновлено", auto_now=True)
    institution = models.ForeignKey(
        "institution.Institution", verbose_name="Заведение", on_delete=models.CASCADE
    )
    institution_branch = models.ForeignKey(
        "institution.InstitutionBranch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_item_groups",
        verbose_name="Филиал заведения",
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, verbose_name="Заказ", related_name="item_groups"
    )
    products_sum = models.IntegerField(verbose_name="Сумма продуктов", default=0)
    delivering_sum = models.IntegerField(verbose_name="Сумма доставки", default=0)
    total_sum = models.IntegerField(verbose_name="Общая сумма", default=0)
    commission = models.IntegerField(verbose_name="Комиссия", default=0)

    class Meta:
        verbose_name = "Группа продуктов для заказа"
        verbose_name_plural = "Группы продуктов для заказа"

    def __str__(self):
        return f"Группа для заказа №{self.order.id}"

    @property
    def institution_address_branch(self):
        if self.institution_branch and self.institution_branch.address:
            return self.institution_branch.address
        return None


class OrderItem(models.Model):
    order_item_group = models.ForeignKey(
        OrderItemGroup, on_delete=models.CASCADE, verbose_name="Группа", related_name="items"
    )
    is_incident = models.BooleanField(default=False, verbose_name="Инцидентный продукт")
    incident_product = models.ForeignKey("product.Product", null=True, blank=True, on_delete=models.SET_NULL, related_name="incident_items", verbose_name="Инцидентный продукт")
    product = models.ForeignKey("product.Product", verbose_name="Продукт", on_delete=models.CASCADE)
    count = models.IntegerField(verbose_name="Количество")
    total_sum = models.IntegerField(verbose_name="Сумма")
    options = models.ManyToManyField(
        "product.OptionItem", related_name="order_items", blank=True, verbose_name="Опции"
    )

    class Meta:
        verbose_name = "Продукт заказа"
        verbose_name_plural = "Продукты заказа"

    @property
    def price(self):
        return self.total_sum / self.count

class TelegramMessage(models.Model):
    order = models.OneToOneField("Order", null=True, blank=True, on_delete=models.CASCADE, related_name="message")

    message_id = models.PositiveIntegerField(null=True, blank=True)
    message_id2 = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)  # Xabar qachon saqlangani
    updated_at = models.DateTimeField(auto_now=True)      # Oxirgi o'zgarish

    def __str__(self):
        return f"Order #{self.order_id} - Message #{self.message_id}"