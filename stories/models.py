import mimetypes

from django.core.exceptions import ValidationError
from django.db import models

from base.models import TimeStampedModel
from institution.models import Institution

# Create your models here.


def validate_mp4_file(value):
    mime_type, encoding = mimetypes.guess_type(value.name)
    allowed_mime_types = ["video/mp4", "image/jpeg", "image/png", "image/gif"]
    if mime_type not in allowed_mime_types:
        raise ValidationError("Файл должен быть в формате MP4 или изображением (JPEG, PNG, GIF).")


class Stories(TimeStampedModel):
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Заголовок")
    image_stories_ru = models.FileField(
        upload_to="stories/",
        blank=True,
        null=True,
        validators=[validate_mp4_file],
        verbose_name="Файл сториса русский",
    )
    image_stories_uz = models.FileField(
        upload_to="stories/",
        blank=True,
        null=True,
        validators=[validate_mp4_file],
        verbose_name="Файл сториса узбекский",
    )
    image_stories_en = models.FileField(
        upload_to="stories/",
        blank=True,
        null=True,
        validators=[validate_mp4_file],
        verbose_name="Файл сториса английский",
    )
    logo_stories_ru = models.FileField(
        upload_to="stories/",
        blank=True,
        null=True,
        validators=[validate_mp4_file],
        verbose_name="Лого сториса русский",
    )
    logo_stories_uz = models.FileField(
        upload_to="stories/",
        blank=True,
        null=True,
        validators=[validate_mp4_file],
        verbose_name="Лого сториса узбекский",
    )
    logo_stories_en = models.FileField(
        upload_to="stories/",
        blank=True,
        null=True,
        validators=[validate_mp4_file],
        verbose_name="Лого сториса английский",
    )
    start_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата старта")
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата окончания",
    )
    is_active = models.BooleanField(default=False, verbose_name="Активность")
    position = models.IntegerField(default=0, verbose_name="Номер позиции")
    url_link = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ссылка")
    institution = models.ForeignKey(to=Institution, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Сторис (видео) от {self.created_at.strftime('%Y-%m-%d %H:%M:%S')} числа"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "История"
        verbose_name_plural = "Истории"

    def get_related_regions(self):
        from address.models import Region

        return Region.objects.filter(stories_set__in=self.regions.all())


class StoriesToRegion(models.Model):
    story = models.ForeignKey(
        Stories, on_delete=models.CASCADE, related_name="regions", verbose_name="Сторис"
    )
    region = models.ForeignKey(
        "address.Region",
        on_delete=models.CASCADE,
        related_name="stories_set",
        verbose_name="Регион",
    )
