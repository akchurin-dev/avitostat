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
from messaging.api import get_chats, MessagingAPISync
from messaging.bad_mes_report.utils_bad_messaging_report import chats_timestamp_to_datetime
from messaging.bad_mes_report.utils_chats import filter_chats_for_last_period, \
    filter_chats_only_with_text, filter_by_bot_answered_chat_ids
from asgiref.sync import async_to_sync
from telegram_bot import bot
from avito_account.models.models import AvitoAccount
from base.settings import ENVIRONMENT
from chat_bot.ai_utils import ai_answer_with_contacts, chat_summary_ai_generator
from chat_bot.api.core import AvitoMessengerSync
from chat_bot.models import AiChatBot, ChatBotTask
from messaging.api import get_chats_last_50_messages
from celery import shared_task

class AiAnswerAvitoClass:
    @staticmethod
    def task_contacts_save(new_task_id: str, ai_answer: dict, is_incoming: bool):
        #Core fields
        new_task = ChatBotTask.objects.filter(message_id=new_task_id).last()
        new_task.is_incoming = is_incoming

        if ai_answer:
            new_task.answer_text = ai_answer.get("answer", "Не предусмотрено")
            new_task.tokens_completion = ai_answer.get("tokens_completion")
            new_task.tokens_prompt = ai_answer.get("tokens_prompt")

            #Contact fields
            contacts = ai_answer.get("contacts")
            if contacts is not None:
                new_task.city = contacts.get("city", None)
                new_task.address = contacts.get("address", None)
                new_task.mobile = contacts.get("mobile", None)
                new_task.whatsapp = contacts.get("whatsapp", None)
                new_task.telegram = contacts.get("telegram", None)
                new_task.email = contacts.get("email", None)

        new_task.save()

    @staticmethod
    @shared_task
    def chat_contacts_checker_task(avito_account: AvitoAccount, chat_id: str):
        celery_logger.warning(f"chat_contacts_checker_task STARTED")
        chat_with_messages = MessagingAPISync.get_chats_last_50_messages(avito_account, chats=[{"id": chat_id}])
        ai_assistant = AiChatBot.objects.filter(avito_account=avito_account).last()
        ai_answer = ai_answer_with_contacts(ai_assistant, chat=chat_with_messages[0].get("messages"))
        return ai_answer.get("contacts")

    @staticmethod
    @shared_task
    def ai_answer_sender_task(avito_account_id, chat_id, chat_bot_id, new_task_id):
        shared_task.__name__ = f"ai_answer_{new_task_id}"
        celery_logger.warning(f"ai_answer_sender STARTED")
        avito_account = AvitoAccount.objects.get(pk=avito_account_id)
        chat_bot = AiChatBot.objects.get(pk=chat_bot_id)
        chat_with_messages = MessagingAPISync.get_chats_last_50_messages(avito_account, chats=[{"id": chat_id}])
        # ответ генерируем только если менеджер всё ещё не ответил
        actual_message = chat_with_messages[0].get("messages")[-1]
        if actual_message.get("type") == "system":  # тк при номере последним становится уже сообщение с предупреждением
            actual_message = chat_with_messages[0].get("messages")[-2]
        if actual_message.get("direction") == "in" and actual_message.get("type") == "text":
            ai_answer = ai_answer_with_contacts(chat_bot, chat_with_messages[0].get("messages")[:])
            if ai_answer:
                message_text = ai_answer.get("answer") + "…"
                AvitoMessengerSync.send_message_to_avito(avito_account, avito_account.id, chat_id, message_text)
                AiAnswerAvitoClass.task_contacts_save(new_task_id, ai_answer, is_incoming=True)
                contacts = ai_answer.get("contacts")
                if contacts is not None:
                    ChatBotSummaryReportClass.summary_sender_main_task(avito_account_id, chat_id)


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
    def batch_files_sender_to_tg_not_used():
        #TODO передача и парсинг путей файлов не реализованы
        try:
            file_paths = [file for file in Path("chat_bot/pdfs").iterdir() if file.is_file()]
            media_group = list()
            for i, f in enumerate(file_paths):
                try:
                    with open(f, "rb") as fin:
                        fin.seek(0)
                        media_group.append(InputMediaDocument(media=types.FSInputFile(f)))
                    # Send the media group if it reaches 10 files or if it's the last file
                    if (i + 1) % 10 == 0 or (i + 1) == len(file_paths):
                        bot.send_raw(
                            chat_id=-4221870448,
                            function="send_media_group",
                            media=media_group)
                        media_group = list()  # Reset the media group after sending
                        celery_logger.info("Media group sent successfully.")
                        time.sleep(40) #for enable flood control
                except Exception as e:
                    celery_logger.error(f"Error processing file {f}: {e}")
        except Exception as e:
            celery_logger.error(f"Error sending media group: {e}")

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
                    disable_web_page_preview=True,
                )
                    text = text[4000:]
                except Exception as e:
                    pass

class BotStatisticsDailyReportClass(PdfReportBaseClass):
    @staticmethod
    @shared_task
    def statistics_sender_main_task():
        avito_accounts = AvitoAccount.objects.all()
        celery_logger.warning(f"statistics_sender_main_task STARTED for {len(avito_accounts)} accounts")
        if ENVIRONMENT == "DEVELOPMENT":
            avito_accounts = AvitoAccount.objects.filter(id=163634833)
        for avito_account in avito_accounts:
            try:
                chat_bot_is_active_flag = hasattr(avito_account, "ai_chat_bots") and avito_account.ai_chat_bots.is_active
                need_report_flag = hasattr(avito_account, "ai_chat_bots") and avito_account.ai_chat_bots.statistics_daily_report
                if chat_bot_is_active_flag and need_report_flag:
                    celery_logger.warning("processing")
                    celery_logger.info(f"need_report_flag - {need_report_flag}")
                    if ENVIRONMENT == "DEVELOPMENT":
                        async_to_sync(avito_account.update_refresh_token_async)()
                    BotStatisticsDailyReportClass.statistics_sender_small_task.delay(avito_account.id)
                else:
                    celery_logger.warning(f"skipped avito_account - {avito_account.name}")
                    celery_logger.info(f"chat_bot_is_active_flag - {chat_bot_is_active_flag}")
                    celery_logger.info(f"need_report_flag - {need_report_flag}")
            except Exception as error:
                celery_logger.exception(f"statistics_sender_main_task error - {error}", exc_info=True)

    @staticmethod
    @shared_task
    def statistics_sender_small_task(avito_account_id):
        avito_account = AvitoAccount.objects.get(id=avito_account_id)
        statistics = BotStatisticsDailyReportClass.get_raw_data(avito_account)
        # TEXT MESSAGE
        if statistics is not None and statistics.get("bot_chats_count") > 0: #
            BotStatisticsDailyReportClass.statistics_txt_sender(str(avito_account.id), statistics)
            # HISTORY PDFs
            BotStatisticsDailyReportClass.history_main_sender(avito_account, statistics)
        else:
            celery_logger.info(f"BotStatisticsDailyReportClass not have Bot_chats for {avito_account.name}, skipped")

    @staticmethod
    def history_main_sender(avito_account: AvitoAccount, statistics: dict):
        chats_with_contacts_ids = statistics.get("chats_with_contacts_ids", [])
        need_history_closed_flag = hasattr(avito_account,"ai_chat_bots") and avito_account.ai_chat_bots.histories_closed
        need_history_open_flag = hasattr(avito_account,"ai_chat_bots") and avito_account.ai_chat_bots.histories_open

        chats = statistics.get("chats", [])
        have_closed_chats = len(chats_with_contacts_ids) > 0
        have_open_chats = (len(chats) - len(chats_with_contacts_ids)) > 0

        if need_history_closed_flag or need_history_open_flag:
            chats = statistics.get("chats") or None

            if chats and have_closed_chats and need_history_closed_flag:
                PdfReportBaseClass.text_sender_to_tg(f"✅ <b>История закрытых переписок"
                                                     f" ({len(chats_with_contacts_ids)} шт) :</b>",
                                                     avito_account.telegram_id)
                for chat in chats:
                    if chat.get("id") in chats_with_contacts_ids:  # ДУМАЮ МОЖНО УБРАТЬ, НО НАДО ПРОВЕРЯТЬ
                        ChatHistoryReportClass.history_pdf_sender_task(avito_account_id=avito_account.id, chat=chat)

            if chats and have_open_chats and need_history_open_flag:
                PdfReportBaseClass.text_sender_to_tg(f"❌ <b>История НЕ закрытых переписок"
                                                     f" ({len(chats) - len(chats_with_contacts_ids)} шт)  :</b>",
                                                     avito_account.telegram_id)
                for chat in chats:
                    if chat.get("id") not in chats_with_contacts_ids:
                        ChatHistoryReportClass.history_pdf_sender_task(avito_account_id=avito_account.id, chat=chat)

    @staticmethod
    def get_html(statistics):
        with open(f"chat_bot/templates/chat_bot/daily_statistics.html", "r", encoding="utf-8") as file:
            clear_template = file.read()
        template = Template(clear_template)
        avito_account_name = statistics.get('avito_account_name') if statistics else "Неизвестно"
        date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        return template.render(avito_account_name=avito_account_name,start_date=date, statistics=statistics)

    @staticmethod
    def statistics_txt_sender(avito_account_id: str, statistics: dict):
        #STATISTICS
        avito_account = AvitoAccount.objects.filter(id=avito_account_id).last()
        tomorrow = (datetime.datetime.now().date()-datetime.timedelta(days=1)).strftime("%d.%m.%Y")

        avito_account_name = statistics.get("avito_account_name")
        total_chats_count = statistics.get("total_chats_count")
        bot_chats_count = statistics.get("bot_chats_count")
        contacts_count = statistics.get("contacts_count")

        text = (
            f"📈 <b>Статистика переписок бота за {tomorrow}</b> 📅\n\n"
            f"👤 <b>Ваш Аккаунт:</b> <code> {avito_account_name}</code>\n"
            f"💬 <b>Всего чатов:</b> <code> {total_chats_count}</code>\n"
            f"🤖 <b>Чатов с ботом:</b> <code> {bot_chats_count}</code>\n"
            f"🎉 <b>Получено контактов:</b> <code> {contacts_count}</code>\n\n"
        )
        BotStatisticsDailyReportClass.text_sender_to_tg(text, avito_account.telegram_id)

    @staticmethod
    def get_raw_data(avito_account, period="day"):
        #TODO после всех манипуляций оптимизировать запросы в БД
        chats = async_to_sync(get_chats)(avito_account, period=period)
        if chats:
            if ENVIRONMENT == "PRODUCTION":last_24_hours = timezone.now() - datetime.timedelta(days=1)
            else: last_24_hours = timezone.now() - datetime.timedelta(days=1)
            chat_bot_tasks = ChatBotTask.objects.filter(avito_account=avito_account,
                                                       created_at__date=last_24_hours.date(),
                                                       tokens_completion__gt=0)
            if chat_bot_tasks.exists():
                bot_answered_mes_ids = list(chat_bot_tasks.values_list("message_id", flat=True).distinct())
                unique_bot_chat_ids = chat_bot_tasks.values_list("chat_id", flat=True).distinct()
                tasks_with_contact = chat_bot_tasks.filter(
                                                    Q(address__isnull=False) & ~Q(address="") |
                                                    Q(mobile__isnull=False) & ~Q(mobile="") |
                                                    Q(whatsapp__isnull=False) & ~Q(whatsapp="") |
                                                    Q(telegram__isnull=False) & ~Q(telegram="") |
                                                    Q(email__isnull=False) & ~Q(email="")
                                                ).values("chat_id").distinct()
                contacts_count = len(tasks_with_contact)
                # Chats with messages getting
                actual_chats = async_to_sync(filter_chats_for_last_period)(chats, period=period)
                actual_chats_with_mes = async_to_sync(get_chats_last_50_messages)(avito_account, actual_chats)
                only_with_text = filter_chats_only_with_text(actual_chats_with_mes)
                bot_chats_with_messages = filter_by_bot_answered_chat_ids(only_with_text, unique_bot_chat_ids)

                statistics = {
                    "avito_account_id": avito_account.id,  # for pdf file naming
                    "avito_account_name": avito_account.name,
                    "total_chats_count": len(only_with_text),
                    "bot_chats_count": len(bot_chats_with_messages),
                    "contacts_count": contacts_count,
                    "chats": bot_chats_with_messages,

                    "bot_answered_mes_ids": bot_answered_mes_ids,
                    "chats_with_contacts_ids": tasks_with_contact.values_list("chat_id", flat=True),
                }
                return statistics

    @staticmethod
    def statistics_pdf_sender_old_version(avito_account_id: str, statistics: dict):

        #STATISTICS
        avito_account = AvitoAccount.objects.filter(id=avito_account_id).last()
        html = BotStatisticsDailyReportClass.get_html(statistics)
        report_name_prefix = f"stat_{avito_account.name}"
        pdf_path = BotStatisticsDailyReportClass.get_pdf(statistics, html, report_name_prefix)
        if pdf_path is not None:
            BotStatisticsDailyReportClass.file_sender_to_tg(pdf_path, avito_account.telegram_id)

        #HISTORY
        chats = statistics.get("chats") or None
        if chats:
            for chat in chats:
                ChatHistoryReportClass.history_pdf_sender_task.delay(avito_account_id=avito_account.id, chat=chat)

class ChatHistoryReportClass(PdfReportBaseClass):

    @staticmethod
    @shared_task
    def history_pdf_sender_task(avito_account_id, chat, summary_html = None):
        """
            1) sometimes we don't have summary_html
        """
        ChatHistoryReportClass.add_from_bot_flag(chat)
        async_to_sync(chats_timestamp_to_datetime)({"chats": [chat]})
        avito_account = AvitoAccount.objects.filter(id=avito_account_id).last()
        statistics = {"avito_account_name": avito_account.name, "avito_account_id": avito_account.id, }
        html_content = ChatHistoryReportClass.get_history_html(chat=chat,statistics=statistics,
                                                               summary_html=summary_html)
        report_name_prefix = f"history_{avito_account.name}"
        pdf_path = ChatBotSummaryReportClass.get_pdf(statistics, html_content, report_name_prefix)
        if pdf_path is not None:
            ChatBotSummaryReportClass.file_sender_to_tg(pdf_path, avito_account.telegram_id)

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
        avito_account = AvitoAccount.objects.filter(id=avito_account_id).last()
        all_tasks = ChatBotTask.objects.filter(chat_id=chat_id)
        if ENVIRONMENT == "PRODUCTION":
            time.sleep(300)
            if all_tasks.filter(summary_sanded=True).exists():
                celery_logger.info(f"Summary report already sent for chat_id {chat_id}.")
                return
        if ENVIRONMENT == "DEVELOPMENT":
            async_to_sync(avito_account.update_refresh_token_async)()

        chat = MessagingAPISync.get_chat_by_id(avito_account, chat_id)
        messages = MessagingAPISync.get_chat_last_50_messages_by_chat_id(avito_account, chat_id)
        chat["messages"] = messages
        if messages is not None and len(messages) > 0:  # skip who can't have bot chats
            chat_summary = chat_summary_ai_generator(avito_account, chat_id)
            if chat_summary is not None:
                ChatBotSummaryReportClass.summary_sender(avito_account, chat_summary, chat, all_tasks)


    @staticmethod
    def summary_sender(avito_account, chat_summary, chat, all_tasks):
        # TEXT MESSAGE
        summary_text = ChatBotSummaryReportClass.get_chat_summary_text(chat_summary, chat)
        celery_logger.info(f"Summary report summary_text {summary_text}.")
        if summary_text and len(summary_text) > 20:  # 20 is random value)
            ChatBotSummaryReportClass.text_sender_to_tg(text=summary_text, telegram_id=avito_account.telegram_id)
            celery_logger.info(f"Summary report text sended to {avito_account.name} telegram.")

        # PDF FILE
        summary_html = ChatBotSummaryReportClass.get_chat_summary_html(chat_summary, chat)
        ChatHistoryReportClass.history_pdf_sender_task.delay(avito_account.id, chat, summary_html)

        last_chat_bot_task = all_tasks.last()
        if last_chat_bot_task is not None:
            # Flag adding for in future we can't be sanding summary_report twice
            last_chat_bot_task.summary_sanded = True
            last_chat_bot_task.save()


    @staticmethod
    def get_chat_summary_html(chat_summary, chat):
        counter = 1
        text = "<div style='font-family: Arial, sans-serif;'><b>Сводка по переписке:</b><br><br>"

        title = chat.get("context").get("value").get("title")
        if title and len(title) == 0: title = "Без названия"
        if title:
            text += f"<p style='margin-left: 20px;'>{counter}. Название объявления: {title}</p>"
            counter += 1

            # INFO ниже может быть без локации например через личку
        location = chat.get("context").get("value").get("location", None)
        if location:
            city_name_from_item = chat.get("context").get("value").get("location").get("title")
        else:
            city_name_from_item = "Без локации"

        if city_name_from_item:
            text += f"<p style='margin-left: 20px;'><b>{counter}. <u>Город обращения: {city_name_from_item}</u></b></p>"
            counter += 1

        for key, value in chat_summary.get("paragraphs").items():
            text += f"<p style='margin-left: 20px;'>{counter}. {value}</p>"
            counter += 1
        text += "</div>"
        return text

    @staticmethod
    def get_chat_summary_text(chat_summary, chat):
        counter = 1
        text = ("🎉 <b>Новый клиент из AVITO 🎉 \n\n</b> "
                "   📋 Сводка по переписке:\n\n")

        title = chat.get("context").get("value").get("title")
        if title and len(title) == 0: title = "Без названия"
        if title:
            text += f"🔹 {counter}. Название объявления: {title}\n"
            counter += 1

        client_name = chat.get("users")[0].get("name")
        if client_name and len(client_name) ==0: client_name = "Без имени"
        if client_name:
            text += f"🔹 {counter}. Имя клиента: {client_name}\n"
            counter += 1

        #INFO ниже может быть без локации например через личку
        location = chat.get("context").get("value").get("location", None)
        if location:
            city_name_from_item = chat.get("context").get("value").get("location").get("title")
        else:
            city_name_from_item = "Без локации"

        if city_name_from_item:
            text += f"🔸 {counter}. <u><b>Город обращения: {city_name_from_item}</b></u> \n"
            counter += 1

        for key, value in chat_summary.get("paragraphs").items():
            text += f"🔹 {counter}. {value} \n"
            counter += 1
        return text
