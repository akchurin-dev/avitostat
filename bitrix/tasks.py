import time

from celery import shared_task
from django.conf import settings
from loguru import logger

from aichatbottask import utils as aichatbottask
from bitrix import models as bitrix_models
from bitrix.utils import ai_chat_bots as bitrix_ai_chat_bots
from bitrix.utils import accounts as bitrix_accounts
from bitrix.utils import bitrix_bots
from bitrix.utils import chats as bitrix_chats
from bitrix.utils import openlines as bitrix_openlines
from chat_bot import ai_utils


@shared_task
def handle_bitrix_message(bitrix_domain: str, dialog_id: str, chat_id: int):
    chat_bot = bitrix_ai_chat_bots.define_chat_bot(bitrix_domain, dialog_id)

    if chat_bot is None:
        bitrix_openlines.redirect_client_to_manager(bitrix_domain, chat_id)
        logger.info(f"Chat bot for bitrix dialog (dialog_id={dialog_id}) not found. Dialog redirected to manager.")
        return

    create_ai_chat_bot_task(bitrix_domain, dialog_id, chat_bot.id)


def create_ai_chat_bot_task(bitrix_domain: str, dialog_id: str, ai_chat_bot_id: int):
    chat_id = f"BITRIX__{bitrix_domain}__{dialog_id}"
    bitrix_account = bitrix_accounts.get_bitrix_account(bitrix_domain, raise_not_exist_exception=True)
    task_id = aichatbottask.create_task(chat_id, bitrix_account.owner_id).id
    ok = aichatbottask.cancel_tasks(chat_id, except_task_id=task_id)
    if ok:
        communicate_with_client.s(bitrix_domain, dialog_id, ai_chat_bot_id, task_id).apply_async(countdown=30)
        logger.info(f"Task {task_id} is PENDING")


@shared_task
def communicate_with_client(bitrix_domain: str, dialog_id: int | str, ai_chat_bot_id: int, task_id: int):
    ok = aichatbottask.change_task_status(task_id, aichatbottask.Task.Status.PREPARING_DATA)
    if not ok:
        return

    chat_bot = bitrix_models.BitrixAIChatBot.objects.get(pk=ai_chat_bot_id)
    messages = bitrix_chats.get_messages(bitrix_domain, dialog_id, messages_count=50)

    bot_id = bitrix_bots.get_bitrix_bot_id(bitrix_domain)
    messages_legacy_format = [{
        "type": "text" if m.text else "not-text",
        "direction": "out" if m.author_id == bot_id else "in",
        "content": {
            "text": m.text,
        }
    } for m in messages]

    ok = aichatbottask.change_task_status(task_id, aichatbottask.Task.Status.ANSWER_GENERATION)
    if not ok:
        return

    if settings.USE_GPT:
        result = ai_utils.ai_answer_with_contacts_typed(chat_bot, messages_legacy_format)
    else:
        time.sleep(3) # simulate gpt answer waiting
        result = ai_utils.AIAnswerWithContacts(
            answer=messages[0].text,
            contacts=ai_utils.AIAnswerContacts(
                address="some address",
                mobile="79991112233",
                whatsapp="79991112233",
                telegram="@sometg",
                email="some@e.mail",
            ),
            tokens_completion=0,
            tokens_prompt=0,
        )

    if result is None:
        raise Exception("OpenAI null result")

    aichatbottask.save_answer(task_id, result)

    ok = aichatbottask.change_task_status(task_id, aichatbottask.Task.Status.ANSWER_SENDING)
    if not ok:
        return

    bitrix_chats.send_message(bitrix_domain, dialog_id, result.answer)

    if result.contacts:
        pass # TODO send summary

    aichatbottask.change_task_status(task_id, aichatbottask.Task.Status.FINISHED)
