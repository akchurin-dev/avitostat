from django.db import models
from avito_account.models.models import logger
from avito_account.tasks import excluded_item_get_title_task


class ExcludedItem(models.Model):
    avito_account = models.ForeignKey(
        'AvitoAccount',
        on_delete=models.CASCADE,
        related_name='excluded_items',
        verbose_name="Аккаунт Avito"
    )
    id = models.IntegerField(
        verbose_name="ID объявления",
        primary_key=True
    )
    title = models.CharField(max_length=255, verbose_name="Название объявления", null=True, blank=True)

    class Meta:
        verbose_name = "Объявление исключённое"
        verbose_name_plural = "Объявления исключённые"
        unique_together = (("avito_account", "id"),)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Запуск таски которая заполнит тайтл
        excluded_item_get_title_task(self)
        logger.warning(f"Новое исключённое объявление добавлено: {self.id}")

    def __str__(self):
        return str(self.id)
