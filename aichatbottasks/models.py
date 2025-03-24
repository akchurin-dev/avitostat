from django.db import models


class Task(models.Model):
    """ 
    Модель позволяет вокруг какого-либо объекта
    создавать множество задач и конкурентно менять их статус
    через функции в модуле aichatbottask/utils.py.
    Например, объектом может выступать чат, а в object_id будет идентификатор чата
    """

    class Status(models.TextChoices):
        PENDING = "PENDING"
        PREPARING_DATA = "PREPARING_DATA"
        ANSWER_GENERATION = "ANSWER_GENERATION"
        ANSWER_SENDING = "ANSWER_SENDING"
        FINISHED = "FINISHED"
        CANCELED = "CANCELED"
        INTERRUPTED = "INTERRUPTED"

    object_id = models.CharField(
        verbose_name="Идентификатор объекта",
        max_length=255,
        db_index=True,
    )

    status = models.CharField(
        verbose_name="Статус",
        choices=Status,
        default=Status.PENDING.value,
        db_index=True,
    )

    class Meta:
        verbose_name = "Задача чат-бота"
        verbose_name_plural = "Задачи чат-ботов"
