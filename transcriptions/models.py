from django.db import models


class Transcription(models.Model):
    text = models.TextField(
        verbose_name="Текст",
    )

    class Meta:
        verbose_name = "Транскрипция"
        verbose_name_plural = "Транскрипции"
