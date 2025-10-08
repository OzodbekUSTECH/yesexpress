from datetime import datetime, timedelta
from random import randint

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager

from fcm_django.models import AbstractFCMDevice

class User(AbstractUser):
    TYPES = (
        ("main_admin", "главный администратор системы"),
        ("admin", "администратор системы"),
        ("institution_owner", "владелец заведения"),
        ("institution_admin", "администратор заведения"),
        ("institution_worker", "работник заведения"),
        ("customer", "клиент"),
        ("operator", "оператор"),
        ("content_manager", "контент менеджер"),
        ("logist", "логист"),
    )
    username = None

    phone_number = models.CharField(max_length=50, verbose_name="Номер телефона", unique=True)
    type = models.CharField(
        max_length=255, choices=TYPES, verbose_name="Тип пользователя", null=True, blank=True
    )
    email = models.EmailField("email address", blank=True, null=True)

    USERNAME_FIELD = "phone_number"

    # one time password fields for registering
    otp = models.IntegerField(verbose_name="SMS код", null=True, blank=True)
    otp_expires = models.DateTimeField(verbose_name="Срок SMS кода", null=True)

    # otp fields for change number
    otp_change_number = models.IntegerField(null=True, blank=True)
    otp_change_number_expires = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    def __str__(self):
        return self.phone_number

    def get_institution(self):
        if self.type == "institution_owner":
            return self.institution_owner
        elif self.type == "institution_admin":
            return self.institution_admin
        elif self.type == "institution_worker":
            return self.worker_branch.institution_branch_id
        return None

    def set_otp(self, number_change=False) -> int:
        otp = randint(1000, 9999)
        expires = datetime.now() + timedelta(seconds=80)

        if number_change:
            self.otp_change_number = otp
            self.otp_change_number_expires = expires
        else:
            self.otp = otp
            self.otp_expires = expires

        self.save(
            update_fields=["otp", "otp_expires", "otp_change_number", "otp_change_number_expires"]
        )
        return otp

    @staticmethod
    def get_worker_types():
        return ["main_admin", "admin", "operator", "content_manager", "logist"]


class CustomFCMDevice(AbstractFCMDevice):
    app_name = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["registration_id"]),
            models.Index(fields=["user"]),
        ]