import datetime
from pathlib import Path
import time

from aiogram import types
from aiogram.types import InputMediaDocument
from asgiref.sync import async_to_sync
from celery import shared_task
from django.db.models import Q, QuerySet
from django.utils import timezone
from jinja2 import Template
import pdfkit
from pydantic import BaseModel
from telegram_bot import bot

from avito_account.models.models import AvitoAccount
from base.celery import celery_logger
from base.settings import ENVIRONMENT
from chat_bot.ai_utils import ai_answer_with_contacts_typed, avito_chat_summary_ai_generator, AIAnswerWithContacts
from chat_bot.api.core import AvitoMessengerSync
from chat_bot.models import AiChatBot, ChatBotTask, CompanyBranch
from chat_bot.utils import avito_chatbots
from chat_bot.utils import chatbot_defining
from chat_bot.utils import companies_branches
from messaging.api import get_chats, MessagingAPISync
from messaging.bad_mes_report.utils_chats import filter_chats_for_last_period, \
    filter_chats_only_with_text, filter_by_bot_answered_chat_ids
from messaging.bad_mes_report.utils_bad_messaging_report import chats_timestamp_to_datetime
from messaging.api import get_chats_last_50_messages
from utils.logging import TraceLogger

class AiAnswerAvitoClass:
    @staticmethod
    def task_contacts_save(new_task_id: str, ai_answer: AIAnswerWithContacts, is_incoming: bool, company_branch: CompanyBranch | None):
        #Core fields
        new_task = ChatBotTask.objects.get(message_id=new_task_id)
        new_task.is_incoming = is_incoming

        new_task.answer_text = ai_answer.answer

        new_task.company_branch = None

        if company_branch:
            new_task.company_branch = company_branch

        if new_task.company_branch is None and ai_answer.nearest_company_branch:
            new_task.company_branch = CompanyBranch.objects.filter(
                account = new_task.avito_account,
                location_slug=ai_answer.nearest_company_branch,
            ).first()

        new_task.tokens_completion = ai_answer.tokens_completion
        new_task.tokens_prompt = ai_answer.tokens_prompt

        if ai_answer.contacts:
            new_task.address = ai_answer.contacts.address
            new_task.mobile = ai_answer.contacts.mobile
            new_task.whatsapp = ai_answer.contacts.whatsapp
            new_task.telegram = ai_answer.contacts.telegram
            new_task.email = ai_answer.contacts.email

        new_task.save()

    @staticmethod
    @shared_task
    def ai_answer_sender_task(
        avito_account_id: int,
        chat_id: str,
        message_id: str,
        new_task_id: str,
        *,
        trace_id: str,
    ) -> None:

        tlogger = TraceLogger(trace_id)
        tlogger.info(f"ai_answer_sender STARTED")

        avito_account = AvitoAccount.objects.get(pk=avito_account_id)

        chat = MessagingAPISync.get_chat_last_50_messages_by_chat_id(
            avito_account=avito_account,
            chat_id=chat_id,
            trace_id=tlogger.trace_id,
        )
        assert "messages" in chat

        # ответ генерируем только если менеджер всё ещё не ответил
        last_message_type = chat["messages"][-1]["type"]
        last_message_id = chat["messages"][-1]["id"]

        if last_message_type == "system":  # тк при номере последним становится уже сообщение с предупреждением
            last_message_type = chat["messages"][-2]["type"]
            last_message_id = chat["messages"][-2]["id"]

        if last_message_type != "text":
            tlogger.info(f"Stop handling. Unsupported message type, got {last_message_type}")
            return

        if last_message_id != message_id:
            tlogger.info(f"Stop handling. Message (id={message_id}) is not actual")
            return
        
        company_branch = companies_branches.define_company_branch(avito_account, chat_id)
        chatbot = chatbot_defining.define_chatbot(avito_account, chat, tlogger=tlogger)

        if chatbot is None:
            tlogger.info("Stop handling. Chatbot not defined")
            return

        if chatbot.read_only:
            tlogger.info("Stop handling. Bot configured to read only")
            return

        if not avito_chatbots.check_chatbot_worktime_now(chatbot):
            tlogger.info("Stop handling. AIChatBot out of work time")
            return

        if avito_chatbots.check_chatbot_shutdown_for_chat(chat_id, chatbot, tlogger=tlogger):
            tlogger.info("Stop handling. Bot stopped for chat")
            return

        ai_answer = ai_answer_with_contacts_typed(chatbot, chat["messages"], ask_location=company_branch is None)
        ai_answer.answer += "..."

        AvitoMessengerSync.send_message_to_avito(avito_account, avito_account.pk, chat_id, ai_answer.answer)
        tlogger.info("Answer was sent to avito successfully")
        AiAnswerAvitoClass.task_contacts_save(new_task_id, ai_answer, is_incoming=True, company_branch=company_branch)
        tlogger.info("AIChatBotTask was updated successfully")

        if chatbot.send_new_contact_report and ai_answer.contacts:
            tlogger.info(f"Contacts was found: {ai_answer.contacts.model_dump()}")
            tlogger.info("Send report")
            ChatBotSummaryReportClass.summary_sender_main_task(avito_account_id, chat_id, trace_id=tlogger.trace_id)
        else:
            tlogger.info({
                "title": "Don't send contacts report",
                "chatbot.send_new_contact_report": chatbot.send_new_contact_report,
                "contacts": ai_answer.contacts.model_dump() if ai_answer.contacts else None,
            })


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
            try:
                bot.send_raw(
                    chat_id=telegram_id,
                    function="send_document",
                    document=types.FSInputFile(pdf_path))
            except:
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
            chat_id = telegram_id
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
    class Statistic(BaseModel):
        avito_account_id: int
        avito_account_name: str | None
        total_chats_count: int
        bot_chats_count: int
        contacts_count: int
        chats: list  # Список структур возвращаемых по запросу api.avito.com/chat/<chat_id>/messages
        bot_answered_mes_ids: list[str]
        chats_with_contacts_ids: list[str]

    @staticmethod
    @shared_task
    def statistics_sender_main_task():
        tlogger = TraceLogger()

        avito_accounts = AvitoAccount.objects.all()
        tlogger.info(f"statistics_sender_main_task STARTED for {len(avito_accounts)} accounts")

        for avito_account in avito_accounts:
            try:
                if ENVIRONMENT == "DEVELOPMENT":
                    async_to_sync(avito_account.update_refresh_token_async)()

                BotStatisticsDailyReportClass.statistics_for_avito_account.delay(avito_account.pk, trace_id=tlogger.trace_id)
            except Exception as error:
                tlogger.warning(f"Exception when start daily statistics for {avito_account.name}. Got '{error}'")
                celery_logger.exception(f"statistics_sender_main_task error - {error}", exc_info=True)

    @staticmethod
    @shared_task
    def statistics_for_avito_account(account_id: int, *, trace_id: str | None = None):
        tlogger = TraceLogger(trace_id)

        account = AvitoAccount.objects.get(pk=account_id)
        aichatbot = AiChatBot.objects.filter(avito_account=account).first()

        if aichatbot is None:
            tlogger.info(f"Skip daily report for {account.name}. AiChatBot is None")
            return

        if not aichatbot.is_active:
            tlogger.info(f"Skip daily report for {account.name}. Chat bot isn't active")
            return

        if not aichatbot.statistics_daily_report:
            tlogger.info(f"Skip daily report for {account.name}. Daily reports are turned off")
            return

        company_branches_id: list[int | None] = [None]
        company_branches_id.extend(CompanyBranch.objects.filter(account=account).values_list("pk", flat=True))

        for company_branch_id in company_branches_id:
            BotStatisticsDailyReportClass.statistics_for_company_branch.delay(account.pk, company_branch_id)

        tlogger.info(f"Daily report launched for {len(company_branches_id)} branches of {account.name}")

    @staticmethod
    @shared_task
    def statistics_for_company_branch(avito_account_id: int, company_branch_id: int | None):
        tlogger = TraceLogger()

        avito_account = AvitoAccount.objects.get(id=avito_account_id)

        company_branch = None
        if company_branch_id:
            company_branch = CompanyBranch.objects.get(pk=company_branch_id)

        tlogger.info(f"Daily report for '{company_branch}' branch of '{avito_account.name}'")

        statistics = BotStatisticsDailyReportClass.get_raw_data(avito_account, company_branch, tlogger=tlogger)

        if not statistics:
            tlogger.info(f"Stop handling {avito_account} ({company_branch}). Statistics is None")
            return

        if statistics.bot_chats_count == 0:
            tlogger.info(f"BotStatisticsDailyReportClass not have Bot_chats for {avito_account.name} ({company_branch}), skipped")
            return

        telegram_id = avito_account.telegram_id

        if company_branch:
            telegram_id = company_branch.telegram_id

        if telegram_id is None:
            tlogger.info(f"Stop handling {avito_account} ({company_branch}). Telegram id is None")
            return

        BotStatisticsDailyReportClass.statistics_txt_sender(telegram_id, statistics)
        BotStatisticsDailyReportClass.history_main_sender(avito_account, telegram_id, statistics, tlogger=tlogger)

        tlogger.info("Finished successfully")

    @staticmethod
    def history_main_sender(avito_account: AvitoAccount, telegram_id: str, statistics: Statistic, *, tlogger: TraceLogger):
        chats_with_contacts_ids = statistics.chats_with_contacts_ids

        aichatbot: AiChatBot | None = getattr(avito_account, "ai_chat_bots", None)

        if aichatbot is None:
            tlogger.info(f"Stop history sending for '{avito_account.name}'. AiChatBot is None")
            return

        if not aichatbot.histories_closed and not aichatbot.histories_open:
            tlogger.info(f"Stop history sending for '{avito_account.name}'. histories_closed and histories_open are both disabled")
            return

        chats = statistics.chats
        have_closed_chats = len(chats_with_contacts_ids) > 0
        have_open_chats = (len(chats) - len(chats_with_contacts_ids)) > 0

        chats = statistics.chats or None

        if chats and have_closed_chats and aichatbot.histories_closed:
            PdfReportBaseClass.text_sender_to_tg(f"✅ <b>История закрытых переписок"
                                                    f" ({len(chats_with_contacts_ids)} шт) :</b>",
                                                    telegram_id)
            for chat in chats:
                if chat.get("id") in chats_with_contacts_ids:  # ДУМАЮ МОЖНО УБРАТЬ, НО НАДО ПРОВЕРЯТЬ
                    ChatHistoryReportClass.history_pdf_sender_task(
                        avito_account_id=avito_account.pk,
                        chat=chat,
                        telegram_id=telegram_id,
                    )

        if chats and have_open_chats and aichatbot.histories_open:
            PdfReportBaseClass.text_sender_to_tg(f"❌ <b>История НЕ закрытых переписок"
                                                    f" ({len(chats) - len(chats_with_contacts_ids)} шт)  :</b>",
                                                    telegram_id)
            for chat in chats:
                if chat.get("id") not in chats_with_contacts_ids:
                    ChatHistoryReportClass.history_pdf_sender_task(
                        avito_account_id=avito_account.pk,
                        chat=chat,
                        telegram_id=telegram_id,
                    )

    @staticmethod
    def get_html(statistics):
        with open(f"chat_bot/templates/chat_bot/daily_statistics.html", "r", encoding="utf-8") as file:
            clear_template = file.read()
        template = Template(clear_template)
        avito_account_name = statistics.get('avito_account_name') if statistics else "Неизвестно"
        date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        return template.render(avito_account_name=avito_account_name,start_date=date, statistics=statistics)

    @staticmethod
    def statistics_txt_sender(telegram_id: str, statistics: Statistic):
        #STATISTICS
        tomorrow = (datetime.datetime.now().date()-datetime.timedelta(days=1)).strftime("%d.%m.%Y")

        avito_account_name = statistics.avito_account_name
        total_chats_count = statistics.total_chats_count
        bot_chats_count = statistics.bot_chats_count
        contacts_count = statistics.contacts_count

        text = (
            f"📈 <b>Статистика переписок бота за {tomorrow}</b> 📅\n\n"
            f"👤 <b>Ваш Аккаунт:</b> <code> {avito_account_name}</code>\n"
            f"💬 <b>Всего чатов:</b> <code> {total_chats_count}</code>\n"
            f"🤖 <b>Чатов с ботом:</b> <code> {bot_chats_count}</code>\n"
            f"🎉 <b>Получено контактов:</b> <code> {contacts_count}</code>\n\n"
        )
        BotStatisticsDailyReportClass.text_sender_to_tg(text, telegram_id)

    @staticmethod
    def get_raw_data(
        avito_account: AvitoAccount,
        company_branch: CompanyBranch | None,
        period="day",
        *,
        tlogger: TraceLogger,
    ) -> Statistic | None:

        chats = async_to_sync(get_chats)(avito_account, period=period)

        if not chats:
            tlogger.info("Chats not found")
            return None

        last_24_hours = timezone.now() - datetime.timedelta(days=1)
        chat_bot_tasks = ChatBotTask.objects.filter(
            avito_account=avito_account,
            company_branch=company_branch,
            created_at__date=last_24_hours.date(),
            tokens_completion__gt=0,
        )

        if not chat_bot_tasks.exists():
            tlogger.info("Tasks not found")
            return None

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
        actual_chats_with_mes = async_to_sync(get_chats_last_50_messages)(avito_account, actual_chats, trace_id=tlogger.trace_id)
        only_with_text = filter_chats_only_with_text(actual_chats_with_mes)
        bot_chats_with_messages = filter_by_bot_answered_chat_ids(only_with_text, unique_bot_chat_ids)

        return BotStatisticsDailyReportClass.Statistic(
            avito_account_id=avito_account.pk,  # for pdf file naming
            avito_account_name=avito_account.name,
            total_chats_count=len(only_with_text),
            bot_chats_count=len(bot_chats_with_messages),
            contacts_count=contacts_count,
            chats=bot_chats_with_messages,
            bot_answered_mes_ids=bot_answered_mes_ids,
            chats_with_contacts_ids=list(tasks_with_contact.values_list("chat_id", flat=True)),
        )

    @staticmethod
    def statistics_pdf_sender_old_version(avito_account_id: str, statistics: dict):

        #STATISTICS
        avito_account = AvitoAccount.objects.get(id=avito_account_id)
        html = BotStatisticsDailyReportClass.get_html(statistics)
        report_name_prefix = f"stat_{avito_account.name}"
        pdf_path = BotStatisticsDailyReportClass.get_pdf(statistics, html, report_name_prefix)
        if pdf_path is not None:
            BotStatisticsDailyReportClass.file_sender_to_tg(pdf_path, avito_account.telegram_id)

        #HISTORY
        chats = statistics.get("chats") or None
        if chats:
            for chat in chats:
                ChatHistoryReportClass.history_pdf_sender_task.delay(avito_account_id=avito_account.pk, chat=chat)


class ChatHistoryReportClass(PdfReportBaseClass):
    @staticmethod
    @shared_task
    def history_pdf_sender_task(avito_account_id, chat, summary_html = None, telegram_id: str | None = None):
        """
            1) sometimes we don't have summary_html
        """
        ChatHistoryReportClass.add_from_bot_flag(chat)
        async_to_sync(chats_timestamp_to_datetime)({"chats": [chat]})
        avito_account = AvitoAccount.objects.get(id=avito_account_id)
        statistics = {"avito_account_name": avito_account.name, "avito_account_id": avito_account.pk, }
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
    def summary_sender_main_task(avito_account_id, chat_id, *, trace_id: str | None = None):
        tlogger = TraceLogger(trace_id)

        avito_account = AvitoAccount.objects.filter(id=avito_account_id).last()

        if avito_account is None:
            raise Exception(f"Avito with id={avito_account_id} account isn't found")

        all_tasks = ChatBotTask.objects.filter(chat_id=chat_id)

        if ENVIRONMENT == "PRODUCTION":
            time.sleep(300)
        if ENVIRONMENT == "DEVELOPMENT":
            async_to_sync(avito_account.update_refresh_token_async)()

        if all_tasks.filter(summary_sanded=True).exists():
            tlogger.info(f"Summary report already sent for chat_id {chat_id}.")
            return

        chat = MessagingAPISync.get_chat_by_id(avito_account, chat_id)
        messages = MessagingAPISync.get_chat_last_50_messages_by_chat_id(avito_account, chat_id).get("messages")
        assert messages
        chat["messages"] = messages

        if messages is None or len(messages) == 0:
            tlogger.info("Stop summary sending. No messages in chat")
            return

        chat_summary = avito_chat_summary_ai_generator(avito_account, chat_id, tlogger=tlogger)
        if chat_summary:
            ChatBotSummaryReportClass.summary_sender(avito_account, chat_summary, chat, all_tasks, tlogger=tlogger)
        else:
            tlogger.info(f"Chat summary is empty, got {chat_summary}")

    @staticmethod
    def summary_sender(avito_account, chat_summary, chat, all_tasks: QuerySet[ChatBotTask], *, tlogger: TraceLogger):
        summary_text = ChatBotSummaryReportClass.get_chat_summary_text(chat_summary, chat)
        tlogger.info(f"Summary report summary_text {summary_text}.")

        telegram_id = avito_account.telegram_id
        location = "Location not defined"

        task_with_company_branch = all_tasks.filter(company_branch__isnull=False).order_by("created_at").last()
        if task_with_company_branch:
            assert task_with_company_branch.company_branch
            telegram_id = task_with_company_branch.company_branch.telegram_id
            location = task_with_company_branch.company_branch.location

        if summary_text and len(summary_text) > 20:  # 20 is random value)
            tlogger.info(f"Send summary report to chat (tg_id={telegram_id}) of '{avito_account.name}' ({location})")
            ChatBotSummaryReportClass.text_sender_to_tg(text=summary_text, telegram_id=telegram_id)
            tlogger.info(f"Summary report was sent successfully")
        else:
            tlogger.info(f"Summary text is empty or not enought long")

        summary_html = ChatBotSummaryReportClass.get_chat_summary_html(chat_summary, chat)
        tlogger.info(f"Send history pdf to chat (tg_id={telegram_id}) of '{avito_account.name}' ({location})")
        ChatHistoryReportClass.history_pdf_sender_task.delay(avito_account.id, chat, summary_html, telegram_id)

        last_chat_bot_task = all_tasks.last()
        if last_chat_bot_task is not None:
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
