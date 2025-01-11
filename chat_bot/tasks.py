import datetime
from pathlib import Path
from aiogram import types
import pdfkit
from jinja2 import Template
from django.db.models import Q
from django.utils import timezone
from messaging.api import get_chats
from messaging.bad_mes_report.utils_chats import filter_chats_for_last_period, \
    filter_chats_only_with_text, filter_by_bot_answered_chat_ids
from asgiref.sync import async_to_sync, sync_to_async
from telegram_bot import bot
from avito_account.models.models import AvitoAccount
from base.settings import ENVIRONMENT
from chat_bot.ai_utils import ai_answer_assist, chat_summary_generator
from chat_bot.api.core import send_message_to_avito, read_chat
from chat_bot.models import AiChatBot, ChatBotTask
from messaging.api import get_chats_last_50_messages
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
            message_text = ai_answer.get("answer")
            await send_message_to_avito(avito_account, user_id, chat_id, message_text)
            await chat_bot_task_dao_save(new_task_id, ai_answer)
            if ai_answer.get("contacts") is not None:
                await send_chat_summary(avito_account.id, chat_id)


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

    if ENVIRONMENT == 'DEVELOPMENT':
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


class ChatBotDailyReport:

    @staticmethod
    @shared_task
    def report_sender_main_task():
        avito_accounts = AvitoAccount.objects.all()

        for avito_account in avito_accounts:
            chat_bot_is_active = hasattr(avito_account, "ai_chat_bots") and avito_account.ai_chat_bots.is_active
            if chat_bot_is_active is not None and chat_bot_is_active:
                if ENVIRONMENT == "DEVELOPMENT":
                    async_to_sync(avito_account.update_refresh_token_async)()

                    ChatBotDailyReport.celery_sender_small_task.delay(avito_account.id)

    @staticmethod
    @shared_task
    def celery_sender_small_task(avito_account_id):
        avito_account = AvitoAccount.objects.get(id=avito_account_id)
        statistics, chats_total = ChatBotDailyReport.get_raw_data(avito_account)
        if statistics is not None and statistics.get("bot_chats_count") > 0: #skip who can't have bot chats
            pdf_path = ChatBotDailyReport.get_pdf(statistics, chats_total)
            if pdf_path is not None:
                ChatBotDailyReport.file_sender_to_tg(pdf_path, avito_account.telegram_id)

    @staticmethod
    def get_raw_data(avito_account, period="week"):
        chats = async_to_sync(get_chats)(avito_account, period=period)
        if chats:
            if ENVIRONMENT == "PRODUCTION":
                last_24_hours = timezone.now() - datetime.timedelta(days=1)
            else:
                last_24_hours = timezone.now() - datetime.timedelta(days=7)

            bot_chats = ChatBotTask.objects.filter(avito_account=avito_account, created_at__gte=last_24_hours, )
            unique_bot_chat_ids = [chat.get("chat_id", None) for chat in bot_chats.values("chat_id").distinct() if
                                   len(bot_chats) > 0]
            contacts = bot_chats.filter(
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
            chats_only_bot_answered = filter_by_bot_answered_chat_ids(only_with_text, unique_bot_chat_ids)

            statistics = {
                "avito_account_id": avito_account.id,  # for pdf file naming
                "avito_account_name": avito_account.name,
                "total_chats_count": len(only_with_text),
                "bot_chats_count": len(unique_bot_chat_ids),
                "contacts_count": contacts,
            }

            return statistics, chats_only_bot_answered

    @staticmethod
    def get_pdf(statistics, chats_total):
        if ENVIRONMENT == 'DEVELOPMENT':
            wkhtmltopdf_path = "/usr/local/bin/wkhtmltopdf"  # For testing 5 items  for economy
        else:
            wkhtmltopdf_path = "/usr/bin/wkhtmltopdf"

        html_content = ChatBotDailyReport.get_html(statistics, chats_total)
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        # Define the directory and file path with the date
        reports_dir = Path("chat_bot/daily_report_pdfs")
        reports_dir.mkdir(parents=True, exist_ok=True)
        # Get the current date in dd.mm.yyyy format
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        pdf_path = reports_dir / f"daily_bot_report_{current_date}_{statistics.get("avito_account_id", "неизвестен id")}.pdf"
        pdfkit.from_string(html_content, pdf_path, configuration=config)
        return pdf_path

    @staticmethod
    def get_html(statistics, chats_total):
        # Загрузка шаблона из файла
        with open("chat_bot/templates/chat_bot/daily_chats_report.html", "r", encoding="utf-8") as file:
            template_content = file.read()
        template = Template(template_content)
        # Данные для подстановки в шаблон
        avito_account_name = statistics.get('avito_account_name') if statistics else "Неизвестно"
        date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        # Генерация HTML с использованием шаблона и данных
        return template.render(avito_account_name=avito_account_name,
                               start_date=date,
                               end_date="delete_this_data",
                               statistics=statistics,
                               chats=chats_total or [], )

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
