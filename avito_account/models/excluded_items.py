from django.db import models


class ExcludedItem(models.Model):
    avito_account = models.ForeignKey(
        'AvitoAccount',
        on_delete=models.CASCADE,
        related_name='excluded_items',
        verbose_name="Аккаунт Avito"
    )
    id = models.BigIntegerField(
        verbose_name="ID объявления",
        primary_key=True
    )

    class Meta:
        verbose_name = "Объявление исключённое"
        verbose_name_plural = "Объявления исключённые"
        unique_together = (("avito_account", "id"),)

    def __str__(self):
        return str(self.id)
