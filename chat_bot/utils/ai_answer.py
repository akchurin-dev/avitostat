import asyncio
import datetime
import time
from pathlib import Path

from aiogram import types
import pdfkit
from aiogram.types import InputMediaDocument
from jinja2 import Template
from django.db.models import Q
from django.utils import timezone

from base.celery import celery_logger
from chat_bot.tasks import ChatBotSummaryReportClass
from messaging.api import get_chats, MessagingAPISync
from messaging.bad_mes_report.utils_bad_messaging_report import chats_timestamp_to_datetime
from messaging.bad_mes_report.utils_chats import filter_chats_for_last_period, \
    filter_chats_only_with_text, filter_by_bot_answered_chat_ids
from asgiref.sync import async_to_sync, sync_to_async
from telegram_bot import bot
from avito_account.models.models import AvitoAccount
from base.settings import ENVIRONMENT
from chat_bot.ai_utils import ai_answer_assist, chat_summary_ai_generator
from chat_bot.api.core import send_message_to_avito, read_chat, AvitoMessengerSync
from chat_bot.models import AiChatBot, ChatBotTask
from messaging.api import get_chats_last_50_messages
from celery import shared_task



class AiAnswerClass:
    @staticmethod
    def chat_bot_task_dao_save(new_task_id: str, ai_answer: dict):
        new_task = ChatBotTask.objects.filter(message_id=new_task_id)
        new_task = new_task[0]
        new_task.answer_text = ai_answer.get("answer")
        new_task.tokens_completion = ai_answer.get("tokens_completion")
        new_task.tokens_prompt = ai_answer.get("tokens_prompt")

        contacts = ai_answer.get("contacts")
        if contacts is not None:
            new_task.city = contacts.get("city", None)
            new_task.address = contacts.get("address", None)
            new_task.mobile = contacts.get("mobile", None)
            new_task.whatsapp = contacts.get("whatsapp", None)
            new_task.telegram = contacts.get("telegram", None)
            new_task.email = contacts.get("email", None)

        new_task.save()

    # @shared_task
    # def ai_answer_sender_task(avito_account_id, chat_id, chat_bot_id, new_task_id):
    #     async_to_sync(ai_answer_sender)(avito_account_id, chat_id, chat_bot_id, new_task_id)

    # TODO  Можно контроль наличия тасок сделать через РЕДИС попробовать чтобы меньше обращений к БД было
    # TODO  хранить chat_id:message_id1, message_id2...
    @shared_task
    @staticmethod
    def ai_answer_sender_task(avito_account_id, chat_id, chat_bot_id, new_task_id):
        celery_logger.warning(f"ai_answer_sender STARTED")
        avito_account = AvitoAccount.objects.get(pk=avito_account_id)
        chat_bot = AiChatBot.objects.get(pk=chat_bot_id)
        chat_with_messages = MessagingAPISync.get_chats_last_50_messages(avito_account, chats=[{"id": chat_id}])
        # ответ генерируем только если менеджер всё ещё не ответил
        actual_message = chat_with_messages[0].get("messages")[-1]
        if actual_message.get("type") == "system":  # тк при номере последним становится уже сообщение с предупреждением
            actual_message = chat_with_messages[0].get("messages")[-2]
        if actual_message.get("direction") == "in" and actual_message.get("type") == "text":
            AvitoMessengerSync.read_chat(avito_account, avito_account.id, chat_id)
            ai_answer = ai_answer_assist(chat_bot, chat_with_messages[0].get("messages")[:])
            if ai_answer:
                message_text = ai_answer.get("answer") + "…"
                AvitoMessengerSync.send_message_to_avito(avito_account, avito_account.id, chat_id, message_text)
                AiAnswerClass.chat_bot_task_dao_save(new_task_id, ai_answer)
                if ai_answer.get("contacts") is not None:
                    if ENVIRONMENT == "PRODUCTION":
                        time.sleep(5) # 300 by default
                    ChatBotSummaryReportClass.summary_sender_main_task.delay(avito_account_id, chat_id)