from asgiref.sync import async_to_sync, sync_to_async

from avito_account.models.models import AvitoAccount
from chat_bot.ai_utils import ai_answer_assist
from chat_bot.api.core import send_message_to_avito, read_chat
from chat_bot.models import AiChatBot, ChatBotTask
from messaging.api import get_chats_messages

from celery import shared_task


@shared_task
def ai_answer_sender_task(avito_account_id, user_id, chat_id, chat_bot_id, message_text, new_task_id):
    async_to_sync(delayed_func_async)(avito_account_id, user_id, chat_id, chat_bot_id, message_text, new_task_id)


# TODO  Можно контроль наличия тасок сделать через РЕДИС попробовать чтобы меньше обращений к БД было
# TODO  хранить chat_id:message_id1, message_id2...

async def delayed_func_async(avito_account_id, user_id, chat_id, chat_bot_id, message_text, new_task_id):
    avito_account = await AvitoAccount.objects.aget(pk=avito_account_id)
    chat_bot = await AiChatBot.objects.aget(pk=chat_bot_id)
    new_task = await sync_to_async(list)(ChatBotTask.objects.filter(message_id=new_task_id))
    chat_with_messages = await get_chats_messages(avito_account, chats=[{"id": chat_id}])
    # ответ генерируем только если менеджер всё ещё не ответил
    if chat_with_messages[0].get("messages")[-1].get("direction") == "in":
        await read_chat(avito_account, user_id, chat_id)
        ai_answer, tokens_completion, tokens_prompt = await ai_answer_assist(chat_bot, chat_with_messages)
        if ai_answer:
            await send_message_to_avito(avito_account, user_id, chat_id, ai_answer.get("answer"))
            new_task[0].answer_text = ai_answer.get("answer")
            new_task[0].tokens_completion = tokens_completion
            new_task[0].tokens_prompt = tokens_prompt
            await new_task[0].asave()
