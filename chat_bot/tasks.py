import asyncio
import datetime
import logging
from pathlib import Path
from aiogram import types
import pdfkit
from jinja2 import Template
from django.db.models import Q
from django.utils import timezone
from messaging.api import get_chats, MessagingAPISync
from messaging.bad_mes_report.utils_bad_messaging_report import chats_timestamp_to_datetime
from messaging.bad_mes_report.utils_chats import filter_chats_for_last_period, \
    filter_chats_only_with_text, filter_by_bot_answered_chat_ids
from asgiref.sync import async_to_sync, sync_to_async
from telegram_bot import bot
from avito_account.models.models import AvitoAccount
from base.settings import ENVIRONMENT, AVITOSTATA_TG_ID
from chat_bot.ai_utils import ai_answer_assist, chat_summary_generator
from chat_bot.api.core import send_message_to_avito, read_chat
from chat_bot.models import AiChatBot, ChatBotTask
from messaging.api import get_chats_last_50_messages
from celery import shared_task
logger = logging.getLogger(__name__)


async def chat_bot_task_dao_save(new_task_id: str, ai_answer: dict):
    new_task = await sync_to_async(list)(ChatBotTask.objects.filter(message_id=new_task_id))
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

    await new_task.asave()


@shared_task
def ai_answer_sender_task(avito_account_id, user_id, chat_id, chat_bot_id, new_task_id):
    async_to_sync(ai_answer_sender)(avito_account_id, user_id, chat_id, chat_bot_id, new_task_id)


# TODO  Можно контроль наличия тасок сделать через РЕДИС попробовать чтобы меньше обращений к БД было
# TODO  хранить chat_id:message_id1, message_id2...

async def ai_answer_sender(avito_account_id, user_id, chat_id, chat_bot_id, new_task_id):
    avito_account = await AvitoAccount.objects.aget(pk=avito_account_id)
    chat_bot = await AiChatBot.objects.aget(pk=chat_bot_id)
    chat_with_messages = await get_chats_last_50_messages(avito_account, chats=[{"id": chat_id}])
    # ответ генерируем только если менеджер всё ещё не ответил
    actual_message = chat_with_messages[0].get("messages")[-1]
    if actual_message.get("type") == "system":  # тк при номере последним становится уже сообщение с предупреждением
        actual_message = chat_with_messages[0].get("messages")[-2]
    if actual_message.get("direction") == "in" and actual_message.get("type") == "text":
        await read_chat(avito_account, user_id, chat_id)
        ai_answer = ai_answer_assist(chat_bot, chat_with_messages[0].get("messages")[:])
        if ai_answer:
            message_text = ai_answer.get("answer") + "…"
            await send_message_to_avito(avito_account, user_id, chat_id, message_text)
            await chat_bot_task_dao_save(new_task_id, ai_answer)
            if ai_answer.get("contacts") is not None:
                if ENVIRONMENT == "PRODUCTION":
                    await asyncio.sleep(300)
                await sync_to_async(ChatBotSummaryReportClass.summary_sender_main_task.delay)(avito_account_id, chat_id)



class PdfReportBaseClass:
    @staticmethod
    def get_pdf(statistics, html_content, report_name_prefix):
        if ENVIRONMENT == 'DEVELOPMENT':
            wkhtmltopdf_path = "/usr/local/bin/wkhtmltopdf"  # For testing 5 items  for economy
        else:
            wkhtmltopdf_path = "/usr/bin/wkhtmltopdf"

        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        # Define the directory and file path with the date
        reports_dir = Path("chat_bot/pdfs")
        reports_dir.mkdir(parents=True, exist_ok=True)
        # Get the current date in dd.mm.yyyy format
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        pdf_path = reports_dir / f"{report_name_prefix}_{current_date}.pdf"
        pdfkit.from_string(html_content, pdf_path, configuration=config)
        return pdf_path

    @staticmethod
    def file_sender_to_tg(pdf_path, telegram_id):
        if pdf_path:
            chat_id = "-4221870448" if ENVIRONMENT == "DEVELOPMENT" else telegram_id
            try:
                bot.send_raw(
                    chat_id=chat_id,
                    function="send_document",
                    document=types.FSInputFile(pdf_path))
            except Exception as e:
                pass

    @staticmethod
    def text_sender_to_tg(text, telegram_id):
        if text:
            chat_id = "-4221870448" if ENVIRONMENT == "DEVELOPMENT" else telegram_id
            while text:
                try:
                    bot.send_raw(
                    chat_id=chat_id,
                    function="send_message",
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                    text = text[4000:]
                except Exception as e:
                    pass

class BotStatisticsDailyReportClass(PdfReportBaseClass):

    @staticmethod
    @shared_task
    def statistics_sender_main_task():
        avito_accounts = AvitoAccount.objects.all()
        if ENVIRONMENT == "DEVELOPMENT":
            avito_accounts = AvitoAccount.objects.filter(id=163634833)
        for avito_account in avito_accounts:
            chat_bot_is_active = hasattr(avito_account, "ai_chat_bots") and avito_account.ai_chat_bots.is_active
            if chat_bot_is_active is not None and chat_bot_is_active:
                if ENVIRONMENT == "DEVELOPMENT":
                    async_to_sync(avito_account.update_refresh_token_async)()
                BotStatisticsDailyReportClass.statistics_sender_small_task.delay(avito_account.id)

    @staticmethod
    @shared_task
    def statistics_sender_small_task(avito_account_id):
        avito_account = AvitoAccount.objects.get(id=avito_account_id)
        statistics = BotStatisticsDailyReportClass.get_raw_data(avito_account)
        if statistics is not None and statistics.get("bot_chats_count") > 0: #
            BotStatisticsDailyReportClass.statistics_pdf_sender_task.delay(str(avito_account.id), statistics)
        else:
            logger.info(f"BotStatisticsDailyReportClass not have Bot_chats for {avito_account.name}, skipped")


    @staticmethod
    @shared_task
    def statistics_pdf_sender_task(avito_account_id: str, statistics: dict):
        #STATISTICS
        avito_account = AvitoAccount.objects.filter(id=avito_account_id).last()
        html = BotStatisticsDailyReportClass.get_html(statistics)
        report_name_prefix = f"stat_{avito_account.name}"
        pdf_path = BotStatisticsDailyReportClass.get_pdf(statistics, html, report_name_prefix)
        if pdf_path is not None:
            BotStatisticsDailyReportClass.file_sender_to_tg(pdf_path, AVITOSTATA_TG_ID)

        #HISTORY
        chats = statistics.get("chats") or None
        if chats:
            for chat in chats:
                ChatHistoryReportClass.history_pdf_sender_main_task.delay(avito_account_id=avito_account.id,
                                                                          chat=chat,
                                                                          telegram_id=AVITOSTATA_TG_ID)

    @staticmethod
    def get_html(statistics):
        with open(f"chat_bot/templates/chat_bot/daily_statistics.html", "r", encoding="utf-8") as file:
            clear_template = file.read()
        template = Template(clear_template)
        avito_account_name = statistics.get('avito_account_name') if statistics else "Неизвестно"
        date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        return template.render(avito_account_name=avito_account_name,start_date=date, statistics=statistics)

    @staticmethod
    def get_raw_data(avito_account, period="day"):
        #TODO после всех манипуляций оптимизировать запросы в БД
        chats = async_to_sync(get_chats)(avito_account, period=period)
        if chats:
            if ENVIRONMENT == "PRODUCTION":
                last_24_hours = timezone.now() - datetime.timedelta(days=1)
            else:
                last_24_hours = timezone.now() - datetime.timedelta(days=1)

            chat_bot_tasks = ChatBotTask.objects.filter(avito_account=avito_account,
                                                       created_at__gte=last_24_hours,
                                                       tokens_completion__gt=0)

            if chat_bot_tasks.exists():
                bot_answered_mes_ids = list(chat_bot_tasks.values_list("message_id", flat=True).distinct())
                unique_bot_chat_ids = chat_bot_tasks.values_list("chat_id", flat=True).distinct()

                contacts = chat_bot_tasks.filter(
                                                    Q(address__isnull=False) & ~Q(address="") |
                                                    Q(mobile__isnull=False) & ~Q(mobile="") |
                                                    Q(whatsapp__isnull=False) & ~Q(whatsapp="") |
                                                    Q(telegram__isnull=False) & ~Q(telegram="") |
                                                    Q(email__isnull=False) & ~Q(email="")
                                                ).values("chat_id").distinct().count()

                # Chats with messages getting
                actual_chats = async_to_sync(filter_chats_for_last_period)(chats, period=period)
                actual_chats_with_mes = async_to_sync(get_chats_last_50_messages)(avito_account, actual_chats)
                only_with_text = filter_chats_only_with_text(actual_chats_with_mes)
                bot_chats_with_messages = filter_by_bot_answered_chat_ids(only_with_text, unique_bot_chat_ids)

                statistics = {
                    "avito_account_id": avito_account.id,  # for pdf file naming
                    "avito_account_name": avito_account.name,
                    "total_chats_count": len(only_with_text),
                    "bot_chats_count": len(unique_bot_chat_ids),
                    "contacts_count": contacts,
                    "chats": bot_chats_with_messages,
                    "bot_answered_mes_ids": bot_answered_mes_ids
                }

                return statistics

class ChatHistoryReportClass(PdfReportBaseClass):

    @staticmethod
    @shared_task
    def history_pdf_sender_main_task(avito_account_id, chat, summary_html = None, telegram_id = None):
        """
            1) sometimes we don't have summary_html
            2) telegram_id is in avito account | it is AVITOSTATA_TG_ID
        """
        # Prepare data
        ChatHistoryReportClass.add_from_bot_flag(chat)
        async_to_sync(chats_timestamp_to_datetime)({"chats": [chat]})

        avito_account = AvitoAccount.objects.filter(id=avito_account_id).last()
        statistics = {"avito_account_name": avito_account.name, "avito_account_id": avito_account.id, }
        html_content = ChatHistoryReportClass.get_history_html(chat=chat,statistics=statistics,
                                                               summary_html=summary_html)
        report_name_prefix = f"history_{avito_account.name}"
        pdf_path = ChatBotSummaryReportClass.get_pdf(statistics, html_content, report_name_prefix)
        if pdf_path is not None:
            telegram_id = telegram_id or avito_account.telegram_id
            ChatBotSummaryReportClass.file_sender_to_tg(pdf_path, telegram_id)

    @staticmethod
    def get_history_html(chat, statistics, summary_html = None):
        """
         -in summary report we add summary_html and in other reports without it
        """
        with open(f"chat_bot/templates/chat_bot/ai_chatting_history.html", "r", encoding="utf-8") as file:
            clear_template = file.read()
        template = Template(clear_template)
        avito_account_name = statistics.get('avito_account_name') if statistics else "Неизвестно"
        date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        client_name = chat.get("users")[0].get("name")
        return template.render(avito_account_name=avito_account_name,
                               client_name=client_name,
                               start_date=date,
                               chat=chat,
                               summary_html=summary_html,)

    @staticmethod
    def add_from_bot_flag(chat):
        chat_bot_tasks = ChatBotTask.objects.filter(chat_id=chat.get("id"), tokens_completion__gt=0)
        bot_answered_mes_ids = list(chat_bot_tasks.values_list("message_id", flat=True).distinct())

        set_from_bot_next = False  # Флаг для следующей итерации
        for message in chat.get("messages", []):
            if set_from_bot_next:
                message["from_bot"] = True
                set_from_bot_next = False  # Сбрасываем флаг
            else:
                message["from_bot"] = False
            if message.get("id") in bot_answered_mes_ids:
                set_from_bot_next = True  # Активируем флаг для следующей итерации
        return chat


class ChatBotSummaryReportClass(PdfReportBaseClass):
    """
    This class generate report when chat_bot got contact from AVITO user.
    Features:
    - Sends a text message with a summary of the chat.
    - Generates a PDF file containing the chat history and sends it.
    """
    @staticmethod
    @shared_task
    def summary_sender_main_task(avito_account_id, chat_id):
        all_tasks = ChatBotTask.objects.filter(chat_id=chat_id)
        if all_tasks.filter(summary_sanded=True).exists():
            logger.info(f"Summary report already sent for chat_id {chat_id}.")
            return
        else:
            avito_account = AvitoAccount.objects.filter(id=avito_account_id).last()
            chat = MessagingAPISync.get_chat_by_id(avito_account, chat_id)
            messages = MessagingAPISync.get_chat_last_50_messages_by_chat_id(avito_account, chat_id)
            chat["messages"] = messages
            if messages is not None and len(messages) > 0:  # skip who can't have bot chats
                chat_summary = chat_summary_generator(avito_account, chat_id)
                if chat_summary is not None:
                    ChatBotSummaryReportClass.summary_sender(avito_account, chat_summary, chat)
                    # здесь неважно в какой именно инстанс для данного чата добавить флаг, главное чтобы он появился
                    last_chat_bot_task = all_tasks.last()
                    if last_chat_bot_task is not None:
                        # Flag adding for in future we can't be sanding summary_report twice
                        last_chat_bot_task.summary_sanded = True
                        last_chat_bot_task.save()


    @staticmethod
    def summary_sender(avito_account, chat_summary, chat):
        # TEXT MESSAGE
        summary_text = ChatBotSummaryReportClass.get_chat_summary_text(chat_summary)
        if summary_text and len(summary_text) > 20:  # 20 is random value)
            ChatBotSummaryReportClass.text_sender_to_tg(text=summary_text, telegram_id=avito_account.telegram_id)
        # PDF FILE
        summary_html = ChatBotSummaryReportClass.get_chat_summary_html(chat_summary)
        ChatHistoryReportClass.history_pdf_sender_main_task.delay(avito_account.id, chat, summary_html)


    @staticmethod
    def get_chat_summary_html(chat_summary):
        counter = 1
        text = "<div style='font-family: Arial, sans-serif;'><b>Сводка по переписке:</b><br><br>"

        for key, value in chat_summary.get("paragraphs").items():
            text += f"<p style='margin-left: 20px;'>{counter}. {value}</p>"
            counter += 1
        text += "</div>"
        return text

    @staticmethod
    def get_chat_summary_text(chat_summary):
        counter = 1
        text = ("🎉 <b>Новый клиент из AVITO 🎉 \n\n</b> "
                "   📋 Сводка по переписке:\n\n")

        for key, value in chat_summary.get("paragraphs").items():
            if "город" in value.lower():
                text += f"🔸 {counter}. <u><b>{value}</b></u> \n"
            else:
                text += f"🔹 {counter}. {value} \n"
            counter += 1
        return text




