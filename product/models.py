from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from modeltrans.fields import TranslationField

from base.models import FlagsModel


class ProductCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    position = models.IntegerField(verbose_name="Позиция")
    uuid = models.UUIDField(blank=True, null=True)
    institution = models.ForeignKey(
        "institution.Institution",
        on_delete=models.CASCADE,
        verbose_name="Заведение",
        related_name="category_set",
    )
    institution_branches = models.ForeignKey(
        'institution.InstitutionBranch',
        on_delete=models.CASCADE,
        verbose_name='Филиалы заведений',
        null=True,
        blank=True,
        related_name='institution_branch_set'
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False, verbose_name="Удален")
    translation_fields = ["name"]
    i18n = TranslationField(translation_fields)

    @property
    def active_products(self):
        return self.product_set.filter(status="active")

    class Meta:
        ordering = ["position"]
        verbose_name = "Категория продуктов"
        verbose_name_plural = "Категории продуктов"

    def __str__(self):
        return self.name_i18n

    def get_translation_fields(self):
        return self.translation_fields


class Product(models.Model):
    STATUS_CHOICES = (("active", "активен"), ("inactive", "неактивен"))
    external_id = models.BigIntegerField(null=True, blank=True, verbose_name="Внешний id")
    uuid = models.UUIDField(blank=True, null=True)

    name = models.CharField(max_length=255, verbose_name="Название")
    short_description = models.CharField(
        max_length=128, null=True, blank=True, verbose_name="Короткое описание"
    )
    description = models.TextField(
        verbose_name="Описание",
        null=True,
        blank=True,
    )
    image = models.ImageField(
        upload_to="product_images/",
        verbose_name="Картинка",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=255, choices=STATUS_CHOICES, default="inactive", verbose_name="Статус"
    )
    price = models.IntegerField(
        verbose_name="Цена",
        default=0,
    )
    commission = models.IntegerField(
        verbose_name="Комиссия с заказов",
        blank=True,
        null=True,
    )
    old_price = models.IntegerField(null=True, blank=True, verbose_name="Старая цена")
    spic_id = models.CharField(max_length=100, null=True, verbose_name="ИКПУ")
    package_code = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Код упаковки"
    )
    vat = models.IntegerField(
        verbose_name="НДС", default=12, validators=[MaxValueValidator(100), MinValueValidator(0)]
    )
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Категория"
    )
    institution = models.ForeignKey(
        "institution.Institution", on_delete=models.CASCADE, verbose_name="Заведение"
    )
    is_deleted = models.BooleanField(default=False, verbose_name="Удален")
    is_available = models.BooleanField(default=False, verbose_name="Доступен")
    translation_fields = ["name", "description", "short_description"]
    i18n = TranslationField(translation_fields)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.name_i18n


class ProductOption(FlagsModel):
    uuid = models.UUIDField(blank=True, null=True)
    title = models.CharField(max_length=255, verbose_name="Название")
    is_required = models.BooleanField(verbose_name="Обязательный")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="options")

    translation_fields = ["title"]
    i18n = TranslationField(translation_fields)

    class Meta:
        verbose_name = "Дополнение"
        verbose_name_plural = "Дополнения"

    def __str__(self):
        return self.title_i18n

    def get_absolute_url(self):
        return reverse("option-update-admin", kwargs={"pk": self.id})


class OptionItem(models.Model):
    uuid = models.UUIDField(blank=True, null=True)

    title = models.CharField(max_length=255, verbose_name="Название")
    option = models.ForeignKey(
        ProductOption, related_name="items", on_delete=models.SET_NULL, null=True
    )
    adding_price = models.IntegerField(verbose_name="Цена добавления")
    is_default = models.BooleanField(verbose_name="По умолчанию", default=False)
    is_deleted = models.BooleanField(verbose_name="Удален", default=False)

    translation_fields = ["title"]
    i18n = TranslationField(translation_fields)

    class Meta:
        verbose_name = "Элемент дополнения"
        verbose_name_plural = "Элементы дополнения"

    def __str__(self):
        return self.title_i18n


class LikedProducts(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="likes")
    customer = models.ForeignKey(
        "user.User", on_delete=models.CASCADE, related_name="liked_products"
    )

    class Meta:
        unique_together = ["customer", "product"]


class ProductToBranch(models.Model):
    product = models.ForeignKey(
        'product.Product',
        on_delete=models.CASCADE,
        related_name="branches"
    )
    institution_branches = models.ForeignKey(
        'institution.InstitutionBranch',
        on_delete=models.CASCADE,
        related_name='products'
    )
    is_available = models.BooleanField(default=True)
