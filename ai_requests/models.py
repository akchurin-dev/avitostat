from django.db import models


class AIRequest(models.Model):
    tag = models.CharField(
        verbose_name="Тэг",
        max_length=255,
        default="",
        db_index=True,
    )

    model = models.CharField(
        verbose_name="Модель",
        max_length=127,
        db_index=True,
    )

    tokens_completion = models.IntegerField(
        verbose_name="Токены выполнения",
    )

    tokens_prompt = models.IntegerField(
        verbose_name="Токены промпта",
    )

    completion_detail = models.CharField(
        verbose_name="Детали выполнения",
        max_length=255,
        blank=True,
    )

    prompt_detail = models.CharField(
        verbose_name="Детали промпта",
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(
        verbose_name="Создано",
        auto_now_add=True,
        db_index=True,
    )
