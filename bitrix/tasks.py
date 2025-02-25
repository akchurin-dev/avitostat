from asgiref.sync import async_to_sync
from celery import shared_task
from django.conf import settings

from chat_bot import ai_utils
from bitrix import models as bitrix_models
from bitrix.utils import chats as bitrix_chats
from bitrix.utils import bitrix_bots


@shared_task
def generate_answer(bitrix_domain: str, dialog_id: int | str, chat_bot_id: int):
    chat_bot = bitrix_models.AIChatBot.objects.get(pk=chat_bot_id)
    messages = async_to_sync(bitrix_chats.get_messages)(bitrix_domain, dialog_id, messages_count=50)

    bot_id = async_to_sync(bitrix_bots.get_bitrix_bot_id)(bitrix_domain)
    messages_legacy_format = [{
        "type": "text" if m.text else "not-text",
        "direction": "out" if m.author_id == bot_id else "in",
        "content": {
            "text": m.text,
        }
    } for m in messages]

    if settings.USE_GPT:
        result = ai_utils.ai_answer_with_contacts(chat_bot, messages_legacy_format)
        if result is None:
            raise Exception("AI result is null")

        answer = result["answer"]
    else:
        answer = messages[0].text
    
    async_to_sync(bitrix_chats.send_message)(bitrix_domain, dialog_id, answer)
