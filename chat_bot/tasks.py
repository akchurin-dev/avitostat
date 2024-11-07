import asyncio

from asgiref.sync import async_to_sync

from base.celery import celery_app, logger
from avito_account.models.models import AvitoAccount
from chat_bot.ai_utils import ai_answer_assist
from chat_bot.api.core import send_message_to_avito, read_chat
from chat_bot.models import AiChatBot
from messaging.api import get_chats_messages

from celery import shared_task
from celery.result import AsyncResult


# Определяем задачу
@shared_task
def delayed_task(avito_account_id, user_id, chat_id, chat_bot_id, content):
    avito_account = AvitoAccount.objects.get(pk=avito_account_id)
    chat_bot = AiChatBot.objects.get(pk=chat_bot_id)
    chat_with_messages = async_to_sync(get_chats_messages)(avito_account, chats=[{"id": chat_id}])
    # ответ генерируем только если менеджер всё ещё не ответил
    if chat_with_messages[0].get("messages")[-1].get("direction") == "in":
        async_to_sync(read_chat)(avito_account, user_id, chat_id)
        ai_answer = async_to_sync(ai_answer_assist)(chat_bot, chat_with_messages)
        if ai_answer:
            ai_answer += f" answer for {content}"
            async_to_sync(send_message_to_avito)(avito_account, user_id, chat_id, ai_answer)
        print(f"task_ai_answer_for_chat_id executed for chat_id: {chat_id}")


# Функция для создания задачи с задержкой
def create_delayed_task(chat_id, delay=120):
    task_id = f"task_ai_answer_for_chat_id_{chat_id}"  # Уникальный task_id с использованием chat_id
    delayed_task.apply_async((chat_id,), countdown=delay, task_id=task_id)
    return task_id


@celery_app.task(name='ai_messaging.tasks.process_webhook_task')
def process_webhook_task(user_id, data):
    # Запускаем асинхронный код
    asyncio.run(process_webhook_async(user_id, data))


async def process_webhook_async(user_id, data):
    avito_account = await AvitoAccount.objects.aget(id=user_id)
    chat_bot = await AiChatBot.objects.aget(avito_account=avito_account)
    await avito_account.update_refresh_token_async()

    if data.get("payload").get("type") == "message":
        chat_id = data.get("payload").get("value").get("chat_id")
        author_id = data.get("payload").get("value").get("author_id")
        content = data.get("payload").get("value").get("content")

        if author_id != user_id and chat_bot.is_active:
            task_id = f"task_ai_answer_for_chat_id_{chat_id}"
            # Проверяем, существует ли задача с таким task_id и активна ли она
            existing_task = AsyncResult(task_id)
            if existing_task:
                # Если задача активна или ожидает выполнения, отменяем её
                existing_task.revoke(terminate=True)
                logger.info(f"Task {task_id} revoked before creating the new task.")
            # Создаем новую задачу с тем же task_id
            delayed_task.apply(
                (avito_account.id, user_id, chat_id, chat_bot.id, content),
                #  TODO добавить таймер из чат бот инстанса
                countdown=60,
                task_id=task_id
            )
