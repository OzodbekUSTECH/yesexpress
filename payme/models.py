from django.db import models


class PaymeCard(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    expires = models.CharField(max_length=12, verbose_name="Действует до MMYY")
    owner = models.ForeignKey(to="user.User", on_delete=models.CASCADE, verbose_name="Владелец")
    token = models.TextField()
    is_verify = models.BooleanField(null=True, blank=True)
    hidden_number = models.CharField(max_length=20, verbose_name="Номер карты")

    def __str__(self):
        return self.owner

class PaymePayment(models.Model):
    """
    Info about payments
    """

    class StatusChoices(models.IntegerChoices):
        """
        Payment check statuses
        https://developer.help.paycom.uz/ru/metody-subscribe-api/sostoyaniya-cheka
        """

        CREATED = 0, "чек создан"
        TRANSACTION_CREATING = 1, "создание транзакции"
        WRITE_OFF = 2, "списание с карты"
        TRANSACTION_CLOSING = 3, "закрытие транзакции"
        PAYED = 4, "оплачен"
        HOLD = 5, "захолдирован"
        GETTING_HOLDING_COMMAND = 6, "получение команды на холдирование"
        PAUSED = 20, "на паузе"
        ON_CANCEL_QUEUE = 21, "в очереди на отмену"
        CANCELLED = 50, "отменен"

    receipt_id = models.CharField(max_length=255, verbose_name="ID чека")
    total_sum = models.IntegerField(verbose_name="Сумма")
    order = models.ForeignKey("order.Order", on_delete=models.PROTECT)
    card = models.ForeignKey(PaymeCard, on_delete=models.SET_NULL, null=True)
    status = models.IntegerField(choices=StatusChoices.choices, default=StatusChoices.CREATED)
    create_receipt_request = models.JSONField(null=True, blank=True)
    create_receipt_response = models.JSONField(null=True, blank=True)
    pay_receipt_request = models.JSONField(null=True, blank=True)
    pay_receipt_response = models.JSONField(null=True, blank=True)
    confirm_request = models.JSONField(null=True, blank=True)
    confirm_response = models.JSONField(null=True, blank=True)
    cancel_request = models.JSONField(null=True, blank=True)
    cancel_response = models.JSONField(null=True, blank=True)
    set_fiscal_data_request = models.JSONField(null=True, blank=True)
    set_fiscal_data_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
