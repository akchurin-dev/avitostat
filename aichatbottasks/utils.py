import time

from django.db.transaction import atomic

from aichatbottasks.models import Task
from utils.logging import TraceLogger


CANCELABLE_STATUSES = [
    Task.Status.PENDING,
    Task.Status.PREPARING_DATA,
    Task.Status.ANSWER_GENERATION,
]

NOT_CHANGABLE_STATUSES = [
    Task.Status.CANCELED,
    Task.Status.INTERRUPTED,
    Task.Status.FINISHED,
]


def create_task(object_id: str, *, tlogger: TraceLogger) -> Task:
    task = Task.objects.create(
        object_id=object_id,
        status=Task.Status.PENDING.value,
    )
    tlogger.info(f"Task created, id={task.pk}")
    return task


def cancel_tasks(except_task_id: int, *, tlogger: TraceLogger) -> bool:
    """ 
    Cancel all tasks linked with dialog except except_task_id.
    Return True if success and False if task_id was canceled earlier. 
    """

    with atomic():
        except_task = Task.objects.get(pk=except_task_id)

        object_tasks = get_active_tasks_by_object(except_task.object_id)
        object_tasks.select_for_update(no_key=True)

        except_task.refresh_from_db()

        if except_task.status in NOT_CHANGABLE_STATUSES:
            tlogger.info((
                f"Cancel tasks except task (id={except_task_id}) is not success. "
                f"Task (id={except_task_id}) has status '{except_task.status}'"
            ))
            return False

        tasks_to_cancel = object_tasks.filter(status__in=CANCELABLE_STATUSES).exclude(pk=except_task_id)
        canceled_ids = [task.pk for task in tasks_to_cancel]
        tasks_to_cancel.update(status=Task.Status.CANCELED.value)

        tlogger.info(f"Tasks with id in {canceled_ids} was canceled")

    return True


def change_task_status(task_id: int, new_status: Task.Status, *, tlogger: TraceLogger) -> bool:
    """ Return True if status changed successfully and False if task was canceled """

    with atomic():
        task = Task.objects.get(pk=task_id)
        get_active_tasks_by_object(task.object_id).select_for_update(no_key=True)
        task.refresh_from_db()

        if task.status in NOT_CHANGABLE_STATUSES:
            tlogger.info((
                f"Can't change task (id={task_id}) status to '{new_status.value}'. "
                f"Task {task_id} has status '{task.status}'"
            ))
            return False

        Task.objects.filter(pk=task_id).update(status=new_status)

    tlogger.info(f"Task {task_id} is {new_status.value}")
    return True


def get_active_tasks_by_object(object_id: str):
    return Task.objects.filter(object_id=object_id).exclude(
        status__in=NOT_CHANGABLE_STATUSES,
    )


def wait_for_permission_to_start(task_id: int) -> None:
    while True:
        task = Task.objects.get(pk=task_id)

        if task.status == Task.Status.CANCELED.value:
            return

        active_tasks = (
            Task.objects
            .filter(object_id=task.object_id)
            .exclude(pk=task_id)
            .exclude(status__in=NOT_CHANGABLE_STATUSES)
            .exclude(status=Task.Status.PENDING)
        )

        if not active_tasks.exists():
            return

        time.sleep(3)


def interrupt_task_if_error(func):
    def f(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            return res
        except Exception as e:
            change_task_status(
                task_id=kwargs["aichatbottask_id"],
                new_status=Task.Status.INTERRUPTED,
                tlogger=kwargs.get("tlogger") or TraceLogger(kwargs.get("trace_id")),
            )
            raise e

    return f
