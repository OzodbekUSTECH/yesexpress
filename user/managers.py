from django.contrib.auth.base_user import BaseUserManager


class CustomUserManager(BaseUserManager):
    """
    Пользовательский менеджер для модели User
    """

    def create_user(self, phone_number, password, **extra_fields):
        """
        Создает и сохраняет пользователя с данными номером и паролем
        """
        if not phone_number:
            raise ValueError("Номер телефона: обязательное поле")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, phone_number, password, **extra_fields):
        """
        Создает и сохраняет суперпользователя с данными номером и паролем
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперюзер должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперюзер должен иметь is_superuser=True.")
        return self.create_user(phone_number, password, **extra_fields)
