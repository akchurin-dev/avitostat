import time

from django.db.transaction import atomic

from utils.logging import TraceLogger

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

    CANCELABLE_STATUSES = [
        Status.PENDING,
        Status.PREPARING_DATA,
        Status.ANSWER_GENERATION,
    ]

    NOT_CHANGABLE_STATUSES = [
        Status.CANCELED,
        Status.INTERRUPTED,
        Status.FINISHED,
    ]

    object_id = models.CharField(
        verbose_name="Идентификатор объекта",
        max_length=255,
        db_index=True,
    )

    status = models.CharField(
        verbose_name="Статус",
        choices=Status,
        default=Status.PENDING.value,  # type: ignore
        db_index=True,
    )

    created_at = models.DateTimeField(
        verbose_name="Когда создана задача",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        verbose_name="Когда создана задача",
        auto_now=True,
    )

    class Meta:
        abstract = True

    @classmethod
    def cancel_tasks(cls, except_task_id: int, *, tlogger: TraceLogger) -> bool:
        """ 
        Cancel all tasks linked with dialog except except_task_id.
        Return True if success and False if task_id was canceled earlier. 
        """

        with atomic():
            except_task = cls.objects.get(pk=except_task_id)

            object_tasks = cls.get_active_tasks_by_object(except_task.object_id)
            object_tasks.select_for_update(no_key=True)

            except_task.refresh_from_db()

            if except_task.status in cls.NOT_CHANGABLE_STATUSES:
                tlogger.info((
                    f"Cancel tasks except task (id={except_task_id}) is not success. "
                    f"Task (id={except_task_id}) has status '{except_task.status}'"
                ))
                return False

            tasks_to_cancel = object_tasks.filter(status__in=cls.CANCELABLE_STATUSES).exclude(pk=except_task_id)
            canceled_ids = [task.pk for task in tasks_to_cancel]
            tasks_to_cancel.update(status=Task.Status.CANCELED)

            tlogger.info(f"Tasks with id in {canceled_ids} was canceled")

        return True

    @classmethod
    def change_task_status(cls, task_id: int, new_status: Status | str, *, tlogger: TraceLogger) -> bool:
        """ Return True if status changed successfully and False if task was canceled """

        with atomic():
            task = cls.objects.get(pk=task_id)
            cls.get_active_tasks_by_object(task.object_id).select_for_update(no_key=True)
            task.refresh_from_db()

            if task.status in cls.NOT_CHANGABLE_STATUSES:
                tlogger.info((
                    f"Can't change task (id={task_id}) status to '{new_status}'. "
                    f"Task {task_id} has status '{task.status}'"
                ))
                return False

            cls.objects.filter(pk=task_id).update(status=new_status)

        tlogger.info(f"Task {task_id} is {new_status}")
        return True

    @classmethod
    def get_active_tasks_by_object(cls, object_id: str):
        return cls.objects.filter(object_id=object_id).exclude(
            status__in=cls.NOT_CHANGABLE_STATUSES,
        )

    @classmethod
    def wait_for_permission_to_start(cls, task_id: int) -> None:
        while True:
            task = cls.objects.get(pk=task_id)

            if task.status == Task.Status.CANCELED:
                return

            active_tasks = (
                cls.objects
                .filter(object_id=task.object_id)
                .exclude(pk=task_id)
                .exclude(status__in=cls.NOT_CHANGABLE_STATUSES)
                .exclude(status=Task.Status.PENDING)
            )

            if not active_tasks.exists():
                return

            time.sleep(3)

    @classmethod
    def interrupt_task_if_error(cls, func):
        def f(*args, task_id: int, **kwargs):
            try:
                res = func(*args, **kwargs, task_id=task_id)
                return res
            except Exception as e:
                cls.change_task_status(
                    task_id=task_id,
                    new_status=Task.Status.INTERRUPTED,
                    tlogger=kwargs.get("tlogger") or TraceLogger(kwargs.get("trace_id")),
                )
                raise e

        return f

    def cancel_others(self, tlogger: TraceLogger):
        return self.cancel_tasks(
            except_task_id=self.pk,
            tlogger=tlogger,
        )

    def change_status(self, new_status: Status | str, *, tlogger: TraceLogger) -> bool:
        return self.change_task_status(
            task_id=self.pk,
            new_status=new_status,
            tlogger=tlogger,
        )

    def cancel(self, tlogger: TraceLogger):
        return self.change_status(
            new_status=self.Status.CANCELED,
            tlogger=tlogger,
        )
