from django.db import models
from django.utils.html import mark_safe
from modeltrans.fields import TranslationField


class Banner(models.Model):
    img_ru = models.ImageField(upload_to="banners/ru/")
    img_uz = models.ImageField(upload_to="banners/uz/")
    img_en = models.ImageField(upload_to="banners/en/")
    is_active = models.BooleanField(verbose_name="Активность", default=False)
    position = models.IntegerField(verbose_name="Номер позиции", default=0)
    start_date = models.DateTimeField(verbose_name="Дата старта", null=True, blank=True)
    end_date = models.DateTimeField(verbose_name="Дата окончания", null=True, blank=True)
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание", null=True, blank=True)
    category = models.ForeignKey(
        "institution.InstitutionCategory",
        verbose_name="Категория",
        on_delete=models.SET_NULL,
        null=True,
    )
    restaurants = models.ManyToManyField(
        "institution.Institution",
        verbose_name="Рестораны",
        blank=True,
        related_name="banners"
    )

    def image(self):  # new
        return mark_safe(
            '<img src = "http://panel.tuktuk.express/media/{url}" width = "300"/>'.format(
                url=self.img
            )
        )

    translation_fields = ["title", "description"]
    i18n = TranslationField(translation_fields)

    class Meta:
        ordering = ("position",)
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

    def __str__(self):
        return "Баннеры"

    def json(self):
        return {
            "img_ru": self.img_ru.url if self.img_ru else None,
            "img_uz": self.img_uz.url if self.img_uz else None,
            "img_en": self.img_en.url if self.img_en else None,
            "restaurants": [rest.id for rest in self.restaurants.all()]
        }
