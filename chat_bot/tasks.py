from asgiref.sync import async_to_sync, sync_to_async

from avito_account.models.models import AvitoAccount
from chat_bot.ai_utils import ai_answer_assist
from chat_bot.api.core import send_message_to_avito, read_chat
from chat_bot.models import AiChatBot
from messaging.api import get_chats_messages

from celery import shared_task


@shared_task
def delayed_task(avito_account_id, user_id, chat_id, chat_bot_id, content):
    async_to_sync(delayed_func_async)(avito_account_id, user_id, chat_id, chat_bot_id, content)


async def delayed_func_async(avito_account_id, user_id, chat_id, chat_bot_id, content):
    avito_account = await AvitoAccount.objects.aget(pk=avito_account_id)
    chat_bot = await AiChatBot.objects.aget(pk=chat_bot_id)
    chat_with_messages = await get_chats_messages(avito_account, chats=[{"id": chat_id}])
    # ответ генерируем только если менеджер всё ещё не ответил
    if chat_with_messages[0].get("messages")[-1].get("direction") == "in":
        await read_chat(avito_account, user_id, chat_id)
        ai_answer = await ai_answer_assist(chat_bot, chat_with_messages)
        if ai_answer:
            ai_answer += f" answer for {content}"
            await send_message_to_avito(avito_account, user_id, chat_id, ai_answer)
        print(f"task_ai_answer_for_chat_id executed for chat_id: {chat_id}")
