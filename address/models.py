from django.db import models
from modeltrans.fields import TranslationField
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.db import models as postgis_models


class Region(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    points = ArrayField(
        ArrayField(
            models.DecimalField(max_digits=15, decimal_places=13, blank=True, null=True), size=2
        ),
        null=True,
        blank=True,
        default=list,
    )
    polygon = postgis_models.PolygonField(spatial_index=True, null=True, blank=True)
    translation_fields = ["name"]
    i18n = TranslationField(translation_fields)

    class Meta:
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"

    def __str__(self):
        return self.name_i18n


class Address(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название", default="Адрес")
    region = models.ForeignKey("address.Region", on_delete=models.PROTECT, verbose_name="Регион")
    street = models.CharField(max_length=255, verbose_name="Улица", null=True)
    floor = models.IntegerField(verbose_name="Этаж", null=True, blank=True)
    flat_number = models.CharField(
        max_length=255, verbose_name="Номер квартиры", null=True, blank=True
    )
    reference_point = models.CharField(
        max_length=255, verbose_name="Ориентир", null=True, blank=True
    )
    latitude = models.CharField(
        max_length=255, verbose_name="Широта", null=False, default="39.6525787"
    )
    longitude = models.CharField(
        max_length=255, verbose_name="Долгота", null=False, default="66.9568071"
    )
    customer = models.ForeignKey(
        "user.User", on_delete=models.CASCADE, verbose_name="Пользователь", null=True, blank=True
    )
    is_current = models.BooleanField(default=True, verbose_name="Текущий адрес")
    institution = models.OneToOneField(
        "institution.Institution",
        on_delete=models.CASCADE,
        verbose_name="Заведение",
        null=True,
        blank=True,
    )

    is_deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Адрес"
        verbose_name_plural = "Адреса"

    def __str__(self):
        return f"{self.street}"
