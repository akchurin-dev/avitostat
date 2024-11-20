from asgiref.sync import async_to_sync, sync_to_async
from telegram_bot import bot

from avito_account.models.models import AvitoAccount
from base import settings
from chat_bot.ai_utils import ai_answer_assist, chat_summary_generator
from chat_bot.api.core import send_message_to_avito, read_chat
from chat_bot.models import AiChatBot, ChatBotTask
from messaging.api import get_chats_messages
from celery import shared_task


async def chat_bot_task_dao_save(new_task_id: str, ai_answer: dict):
    new_task = await sync_to_async(list)(ChatBotTask.objects.filter(message_id=new_task_id))
    new_task = new_task[0]
    new_task.answer_text = ai_answer.get("answer")
    new_task.tokens_completion = ai_answer.get("tokens_completion")
    new_task.tokens_prompt = ai_answer.get("tokens_prompt")

    contacts = ai_answer.get("contacts")
    if contacts is not None:
        new_task.address = contacts.get("address", None)
        new_task.mobile = contacts.get("mobile", None)
        new_task.whatsapp = contacts.get("whatsapp", None)
        new_task.telegram = contacts.get("telegram", None)
        new_task.email = contacts.get("email", None)

    await new_task.asave()


@shared_task
def ai_answer_sender_task(avito_account_id, user_id, chat_id, chat_bot_id, message_text, new_task_id):
    async_to_sync(ai_answer_sender)(avito_account_id, user_id, chat_id, chat_bot_id, message_text, new_task_id)


# TODO  Можно контроль наличия тасок сделать через РЕДИС попробовать чтобы меньше обращений к БД было
# TODO  хранить chat_id:message_id1, message_id2...

async def ai_answer_sender(avito_account_id, user_id, chat_id, chat_bot_id, message_text, new_task_id):
    avito_account = await AvitoAccount.objects.aget(pk=avito_account_id)
    chat_bot = await AiChatBot.objects.aget(pk=chat_bot_id)
    chat_with_messages = await get_chats_messages(avito_account, chats=[{"id": chat_id}])
    # ответ генерируем только если менеджер всё ещё не ответил
    if chat_with_messages[0].get("messages")[-1].get("direction") == "in":
        await read_chat(avito_account, user_id, chat_id)
        ai_answer = ai_answer_assist(chat_bot, chat_with_messages[0].get("messages")[:])
        if ai_answer:
            message_text = ai_answer.get("answer")
            await send_message_to_avito(avito_account, user_id, chat_id, message_text)
            await chat_bot_task_dao_save(new_task_id, ai_answer)
            if ai_answer.get("contacts") is not None:
                send_chat_summary_task.delay(avito_account.id, chat_id)


@shared_task
def send_chat_summary_task(avito_account_id, chat_id):
    async_to_sync(send_chat_summary)(avito_account_id, chat_id)


async def send_chat_summary(avito_account_id, chat_id):
    avito_account = await AvitoAccount.objects.aget(pk=avito_account_id)
    chat_summary = await chat_summary_generator(avito_account, chat_id)
    counter = 1
    text = ("🆕 Новый клиент из AVITO\n\n"
            "📋 Сводка по переписке:\n\n")

    for key, value in chat_summary.get("paragraphs").items():
        text += f"🔹 {counter}. {value} \n"
        counter += 1

    url = f"https://www.avito.ru/profile/messenger/channel/{chat_id}"
    text += f"\n\n🔗 [Перейти к переписке]({url})"

    if settings.ENVIRONMENT == 'DEVELOPMENT':
        chat_id = "-4221870448"
    else:
        chat_id = avito_account.telegram_id

    while text:
        await sync_to_async(bot.send_raw, thread_sensitive=False)(
            chat_id=chat_id,
            function="send_message",
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        text = text[4000:]
