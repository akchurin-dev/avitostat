import datetime

from django.db.transaction import atomic
from loguru import logger

from aichatbottask.models import Task
from chat_bot import ai_utils


CANCELABLE_STATUSES = [
    Task.Status.PENDING,
    Task.Status.PREPARING_DATA,
    Task.Status.ANSWER_GENERATION,
]


def create_task(chat_id: str, owner_id: int):
    return Task.objects.create(
        chat_id=chat_id,
        owner_id=owner_id,
        status=Task.Status.PENDING.value,
    )


def cancel_tasks(chat_id: str, except_task_id: int) -> bool:
    """ 
    Cancel all tasks linked with dialog except except_task_id.
    Return True if success and False if task_id was canceled earlier. 
    """

    with atomic():
        chat_tasks = get_recent_tasks_by_chat(chat_id)
        chat_tasks.select_for_update(no_key=True)

        except_task = chat_tasks.get(pk=except_task_id)

        if except_task.status == Task.Status.CANCELED.value:
            return False

        chat_tasks.filter(
            status__in=CANCELABLE_STATUSES,
        ).exclude(
            pk=except_task_id,
        ).update(
            status=Task.Status.CANCELED.value,
        )

    return True


def change_task_status(task_id: int, new_status: Task.Status) -> bool:
    """ Return True if status changed successfully and False if task was canceled """

    with atomic():
        status = Task.objects.get(pk=task_id).status

        if status == Task.Status.CANCELED.value:
            logger.info(f"Task {task_id} was CANCELED")
            return False

        Task.objects.filter(pk=task_id).update(status=new_status)

    logger.info(f"Task {task_id} is {new_status.value}")
    return True


def get_recent_tasks_by_chat(chat_id: str):
    return Task.objects.filter(
        chat_id=chat_id,
        created_at__gte=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
    )


def save_answer(task_id: int, answer: ai_utils.AIAnswerWithContacts):
    kwargs = {
        "answer_text": answer.answer,
        "tokens_completion": answer.tokens_completion,
        "tokens_prompt": answer.tokens_prompt,
    }

    if answer.contacts:
        kwargs.update({
            "address": answer.contacts.address,
            "mobile": answer.contacts.mobile,
            "whatsapp": answer.contacts.whatsapp,
            "telegram": answer.contacts.telegram,
            "email": answer.contacts.email,
        })

    Task.objects.filter(pk=task_id).update(**kwargs)
