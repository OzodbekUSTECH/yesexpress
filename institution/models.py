import datetime

from PIL.Image import Resampling
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Q, Prefetch, ForeignKey
from modeltrans.fields import TranslationField

from base.models import FlagsModel, BaseScheduleModel
from product.models import ProductCategory, Product
from .managers import InstitutionBranchManager, InstitutionQuerySet
from PIL import Image


def image_examination(image_path):
    try:
        with Image.open(image_path) as img:
            min_side = min(img.size)
            left = (img.width - min_side) // 2
            top = (img.height - min_side) // 2
            right = left + min_side
            bottom = top + min_side
            cropped_img = img.crop((left, top, right, bottom))
            resized_img = cropped_img.resize((1000, 1000), Resampling.LANCZOS)
            resized_img.save(image_path, quality=75)
    except FileNotFoundError:
        pass


class InstitutionCategory(FlagsModel):
    icon = models.FileField(
        verbose_name="Иконка SVG", upload_to="categories_icons/", null=True, blank=False
    )
    title = models.CharField(max_length=255, verbose_name="Название категории")
    image = models.ImageField(
        upload_to="institution/categories/images/", verbose_name="Фото", null=True
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        image_examination(self.image.path)

    position = models.IntegerField(verbose_name="Позиция в списке", blank=True, null=True)
    translation_fields = ("title",)
    i18n = TranslationField(fields=translation_fields)

    class Meta:
        ordering = ["position"]
        verbose_name = "Категория заведений"
        verbose_name_plural = "Категории заведений"

    def __str__(self):
        return f"{self.title}"

    def get_translation_fields(self):
        return self.translation_fields


class Institution(FlagsModel):
    TYPES = (("restaurant", "ресторан"), ("shop", "магазин"))
    inn = models.CharField(max_length=50, null=True, blank=True, verbose_name="ИНН")
    pinfl = models.CharField(max_length=100, null=True, blank=True, verbose_name="ПИНФЛ")
    name = models.CharField(max_length=255, verbose_name="Название заведения")
    legal_name = models.CharField(max_length=255, null=True, verbose_name="Юридическое название")
    logo = models.ImageField(upload_to="institution/logos/", verbose_name="Логотип", null=True)
    image = models.ImageField(upload_to="institution/images", verbose_name="Картинка", null=True)

    # RKEEPER
    endpoint_url = models.CharField(max_length=300, null=True, blank=True, verbose_name="Хост")
    client_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="Клиент ИД")
    client_secret = models.CharField(max_length=100, null=True, blank=True, verbose_name="Клиент секрет")
    # RKEEPER
    

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # image_examination(self.image.path)
        if self.image and hasattr(self.image, 'path'):
            image_examination(self.image.path)

    is_open = models.BooleanField(default=False, verbose_name="Открыто ли")
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    position = models.IntegerField(default=1, verbose_name="Позиция в списке",  blank=True, null=True)
    category = models.ForeignKey(
        InstitutionCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Категория",
    )
    secondary_categories = models.ManyToManyField(
        InstitutionCategory,
        blank=True,
        verbose_name="Вторичные категории",
        related_name="secondary_institutions",
    )
    admin = models.OneToOneField(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Администратор заведения",
        related_name="institution_admin",
    )
    owner = models.OneToOneField(
        "user.User",
        on_delete=models.PROTECT,
        null=True,
        verbose_name="Владелец заведения",
        related_name="institution_owner",
        blank=True,
    )
    phone_number = models.CharField(max_length=255, verbose_name="Контактный номер")
    start_time = models.TimeField(default=datetime.time(hour=9), verbose_name="Время начала работы")
    end_time = models.TimeField(default=datetime.time(hour=22), verbose_name="Время конца работы")
    # tags = models.TextField(verbose_name='Теги', null=True, blank=True)
    type = models.CharField(verbose_name="Тип заведения", choices=TYPES, max_length=255)
    delivery_by_own = models.BooleanField(verbose_name="Свои курьеры", default=False)
    balance = models.IntegerField(verbose_name="Баланс заведения", default=0, blank=True)
    min_delivery_time = models.IntegerField(
        blank=True, default=30, verbose_name="Минимальное время доставки"
    )
    max_delivery_time = models.IntegerField(
        blank=True, default=50, verbose_name="Максимальное время доставки"
    )
    free_delivery = models.BooleanField(
        default=False,
        verbose_name="Бесплатная доставка",
    )
    is_available = models.BooleanField(default=False, verbose_name="Доступен")
    is_popular = models.BooleanField(default=False, verbose_name="Популярный")
    is_holding = models.BooleanField(default=False, verbose_name="Холдирование")
    cash = models.BooleanField(default=False, verbose_name="Наличная оплата")
    payme = models.BooleanField(default=False, verbose_name="Оплата через Payme")

    translation_fields = ("description",)
    i18n = TranslationField(fields=translation_fields)
    objects = InstitutionQuerySet.as_manager()

    tax_percentage_ordinary = models.IntegerField(
        verbose_name="Процент с заказов обычный",
        validators=[MaxValueValidator(100), MinValueValidator(0)],
        blank=True,
        null=True,
    )
    tax_percentage_restaurant_couriers = models.IntegerField(
        verbose_name="Процент с заказов если курьеры самого ресторана",
        default=0,
        validators=[MaxValueValidator(100), MinValueValidator(0)],
        blank=True,
        null=True,
    )
    tax_percentage_self_pickup = models.IntegerField(
        verbose_name="Процент с заказов если самовывоз",
        default=0,
        validators=[MaxValueValidator(100), MinValueValidator(0)],
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Заведение"
        verbose_name_plural = "Заведения"
        ordering = ["position", "id"]

    def __str__(self):
        return self.name

    def get_translation_fields(self):
        return self.translation_fields

    @property
    def active_categories(self):
        products = Product.objects.filter(Q(status="active") | Q(status="inactive"))
        return (
            ProductCategory.objects.prefetch_related(
                Prefetch("product_set", products),
                "product_set__options",
                "product_set__options__items",
            )
            .annotate(
                product_count=Count(
                    "product", filter=Q(product__status="active") | Q(product__status="inactive")
                )
            )
            .filter(product_count__gte=1, institution=self, is_active=True)
            .order_by("position")
        )


class InstitutionBranch(FlagsModel):
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="branches", verbose_name="Заведение"
    )
    name = models.CharField(max_length=255, verbose_name="Название")
    legal_name = models.CharField(max_length=255, null=True, verbose_name="Юридическое название")
    inn = models.CharField(max_length=50, null=True, blank=True, verbose_name="ИНН")
    pinfl = models.CharField(max_length=100, null=True, blank=True, verbose_name="ПИНФЛ")
    phone_number = models.CharField(max_length=50, null=True, verbose_name="Номер телефона")
    address = models.OneToOneField(
        "address.Address",
        on_delete=models.SET_NULL,
        null=True,
        related_name="institution_branch",
        verbose_name="Адрес",
    )
    is_open = models.BooleanField(default=False, verbose_name="Открыто ли")
    start_time = models.TimeField(default=datetime.time(hour=9), verbose_name="Время начала работы")
    end_time = models.TimeField(default=datetime.time(hour=22), verbose_name="Время конца работы")
    telegram_id_str = models.CharField(
        verbose_name="ID телеграм, разделенные пробелами", max_length=255, null=True, blank=True
    )
    is_available = models.BooleanField(default=False, verbose_name="Доступен")
    min_order_amount = models.IntegerField(default=0, verbose_name="Минимальная сумма заказа")
    places_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="Rkeeper ID")
    min_preorder_minutes = models.IntegerField(
        default=0, verbose_name="Минимальное кол-во минут для предзаказа"
    )
    max_preorder_days = models.IntegerField(
        default=0, verbose_name="Максимальное кол-во дней для предзаказа"
    )
    payme_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Идентификатор Payme"
    )
    payme = models.BooleanField(
        verbose_name="Payme",
        default=False,
    )
    package_addition_amount = models.IntegerField(
        default=0, verbose_name="Сумма для добавления пакета в корзину"
    )
    package_amount = models.IntegerField(
        default=0, verbose_name="Сумма пакета"
    )
    package_spic_id = models.CharField(max_length=100, null=True, verbose_name="ИКПУ пакета")
    package_code = models.CharField(max_length=100, null=True, verbose_name="Код пакета")
    package_vat = models.IntegerField(verbose_name="НДС", default=12, validators=[MaxValueValidator(100), MinValueValidator(0)])

    is_telegram_orders_enabled = models.BooleanField(
        default=False, verbose_name="Принятие заказов через телеграм"
    )
    is_pickup_available = models.BooleanField(default=False, verbose_name="Самовывоз")
    specific_couriers = models.BooleanField(default=False, verbose_name="Специфичные курьеры")
    use_auto_dispatcher = models.BooleanField(
        default=False, verbose_name="Использовать автодиспетчер"
    )

    objects = InstitutionBranchManager.as_manager()

    region_branch = ForeignKey(
        "address.Region",
        null=True,
        on_delete=models.PROTECT,
        related_name="institutionbranchs",
        verbose_name="Регион работы заведения",
    )

    class Meta:
        verbose_name = "Филиал заведения"
        verbose_name_plural = "Филиалы заведения"
        ordering = ["id"]

    def __str__(self):
        return self.name


class InstitutionRating(models.Model):
    customer = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="rates")
    rating = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ["customer", "institution"]

    def __str__(self):
        return f"{self.rating} by {self.customer} on {self.institution}"


class LikedInstitutions(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="likes")
    customer = models.ForeignKey(
        "user.User", on_delete=models.CASCADE, related_name="liked_institutions"
    )

    class Meta:
        unique_together = ["customer", "institution"]


class InstitutionBranchSchedule(BaseScheduleModel):
    institution = models.ForeignKey(
        "institution.InstitutionBranch",
        on_delete=models.CASCADE,
        related_name="schedule_days",
        verbose_name="Заведение",
    )

    class Meta:
        unique_together = [["day_of_week", "institution"]]
        verbose_name = "Расписание заведения"
        verbose_name_plural = "Расписания заведения"


class InstitutionBranchWorker(BaseScheduleModel):
    institution_branch = models.ForeignKey(
        "institution.InstitutionBranch",
        on_delete=models.CASCADE,
        related_name="workers",
        verbose_name="Заведение",
    )
    worker = models.OneToOneField(
        "user.User",
        on_delete=models.PROTECT,
        verbose_name="Владелец заведения",
        related_name="worker_branch",
    )

    class Meta:
        unique_together = [["worker", "institution_branch"]]
        verbose_name = "Работник филиала"
        verbose_name_plural = "Работники филиала"
