import asyncio
from base.celery import celery_app
from ai_messaging.ai_utils import ai_answer_assist
from ai_messaging.api.core import send_message_to_avito
from avito_account.models.models import AvitoAccount
from messaging.api import get_chats_messages


@celery_app.task(name='ai_messaging.tasks.process_webhook_task')
def process_webhook_task(user_id, data):
    # Запускаем асинхронный код
    asyncio.run(process_webhook_async(user_id, data))


async def process_webhook_async(user_id, data):
    avito_account = await AvitoAccount.objects.aget(id=user_id)
    await avito_account.update_refresh_token_async()

    if data.get("payload").get("type") == "message":
        chat_id = data.get("payload").get("value").get("chat_id")
        author_id = data.get("payload").get("value").get("author_id")
        content = data.get("payload").get("value").get("content")

        chat_with_messages = await get_chats_messages(avito_account, chats=[{"id": chat_id}])
        if author_id != user_id:  # Проверка авторства
            ai_answer = await ai_answer_assist(chat=chat_with_messages,
                                               avito_account=avito_account,
                                               test_from_prod=False)
            if ai_answer:
                ai_answer += f" answer for {content}"
                await send_message_to_avito(avito_account, user_id, chat_id, ai_answer)
