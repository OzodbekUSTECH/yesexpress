from django.db import models


class LastVersions(models.Model):
    android_version = models.CharField(max_length=10, verbose_name="Версия андроида")
    ios_version = models.CharField(max_length=10, verbose_name="IOS версия")

    class Meta:
        verbose_name = "Последние версии"
        verbose_name_plural = "Последние версии"

    def __str__(self):
        return "Последние версии"
