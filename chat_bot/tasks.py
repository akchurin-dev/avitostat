import asyncio
import datetime
from pathlib import Path

from aiogram import types
import pdfkit
from aiogram.types import InputMediaDocument
from jinja2 import Template
from django.db.models import Q
from django.utils import timezone

from base.celery import logger
from messaging.api import get_chats, MessagingAPISync
from messaging.bad_mes_report.utils_bad_messaging_report import chats_timestamp_to_datetime
from messaging.bad_mes_report.utils_chats import filter_chats_for_last_period, \
    filter_chats_only_with_text, filter_by_bot_answered_chat_ids
from asgiref.sync import async_to_sync, sync_to_async
from telegram_bot import bot
from avito_account.models.models import AvitoAccount
from base.settings import ENVIRONMENT
from chat_bot.ai_utils import ai_answer_assist, chat_summary_ai_generator
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
        new_task.city = contacts.get("city", None)
        new_task.address = contacts.get("address", None)
        new_task.mobile = contacts.get("mobile", None)
        new_task.whatsapp = contacts.get("whatsapp", None)
        new_task.telegram = contacts.get("telegram", None)
        new_task.email = contacts.get("email", None)

    await new_task.asave()


@shared_task
def ai_answer_sender_task(avito_account_id, chat_id, chat_bot_id, new_task_id):
    async_to_sync(ai_answer_sender)(avito_account_id, chat_id, chat_bot_id, new_task_id)


# TODO  Можно контроль наличия тасок сделать через РЕДИС попробовать чтобы меньше обращений к БД было
# TODO  хранить chat_id:message_id1, message_id2...

async def ai_answer_sender(avito_account_id, chat_id, chat_bot_id, new_task_id):
    logger.info(f"ai_answer_sender 1 log info")
    logger.warning(f"ai_answer_sender 1 log warning")
    logger.exception(f"ai_answer_sender 1 log exception")
    avito_account = await AvitoAccount.objects.aget(pk=avito_account_id)
    chat_bot = await AiChatBot.objects.aget(pk=chat_bot_id)
    chat_with_messages = await get_chats_last_50_messages(avito_account, chats=[{"id": chat_id}])
    # ответ генерируем только если менеджер всё ещё не ответил
    actual_message = chat_with_messages[0].get("messages")[-1]
    if actual_message.get("type") == "system":  # тк при номере последним становится уже сообщение с предупреждением
        actual_message = chat_with_messages[0].get("messages")[-2]
    if actual_message.get("direction") == "in" and actual_message.get("type") == "text":
        await read_chat(avito_account, avito_account.id, chat_id)
        ai_answer = ai_answer_assist(chat_bot, chat_with_messages[0].get("messages")[:])
        if ai_answer:
            message_text = ai_answer.get("answer") + "…"
            await send_message_to_avito(avito_account, avito_account.id, chat_id, message_text)
            await chat_bot_task_dao_save(new_task_id, ai_answer)
            if ai_answer.get("contacts") is not None:
                if ENVIRONMENT == "PRODUCTION":
                    await asyncio.sleep(5) # 300 by default
                logger.info(f"ai_answer_sender 2 log info")
                logger.warning(f"ai_answer_sender 2 log warning")
                logger.exception(f"ai_answer_sender 2 log exception")
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

    @staticmethod
    def batch_files_sender_to_tg():
        file_paths = [file for file in Path("chat_bot/pdfs").iterdir() if file.is_file()]
        media_group = list()

        for f in file_paths:
            with open(f, "rb") as fin:
                # Up to 1024 characters.
                # https://core.telegram.org/bots/api#inputmediadocument
                caption = f"Total students in {f}: {len(fin.readlines())}\n"
                # After the len(fin.readlines()) file's current position
                # will be at the end of the file. seek(0) sets the position
                # to the begining of the file so we can read it again during
                # sending.
                fin.seek(0)
                media_group.append(types.FSInputFile(f))

        # bot.send_media_group(-4221870448, media=media_group)

        bot.send_raw(
            chat_id=-4221870448,
            function="send_media_group",
            media=media_group)

        # bot.send_media_group()

    # @staticmethod
    # def batch_files_sender_to_tg(pdf_paths: list, telegram_id: str, batch_size: int = 10):
    #     """
    #     Отправляет несколько PDF файлов группами по 2-10 файлов в одном сообщении.
    #
    #     Args:
    #         pdf_paths (list): Список путей к PDF файлам (максимум 20)
    #         telegram_id (str): ID телеграм чата для отправки
    #         batch_size (int): Размер группы файлов (по умолчанию 10)
    #     """
    #     if not pdf_paths:
    #         logger.warning("batch_files_sender_to_tg: Список файлов пуст")
    #         return
    #
    #     logger.info(f"batch_files_sender_to_tg: Начало отправки {len(pdf_paths)} файлов")
    #
    #     # Ограничиваем количество файлов до 20
    #     pdf_paths = pdf_paths[:20]
    #
    #     # Убеждаемся что размер группы от 2 до 10
    #     batch_size = max(2, min(10, batch_size))
    #     logger.info(f"batch_files_sender_to_tg: Размер группы установлен на {batch_size}")
    #
    #     chat_id = "-4221870448" if ENVIRONMENT == "DEVELOPMENT" else telegram_id
    #     logger.info(f"batch_files_sender_to_tg: Отправка в чат {chat_id}")
    #
    #     # Разбиваем файлы на группы
    #     total_batches = (len(pdf_paths) + batch_size - 1) // batch_size
    #     for i in range(0, len(pdf_paths), batch_size):
    #         current_batch = i // batch_size + 1
    #         batch = pdf_paths[i:i + batch_size]
    #         media_group = []
    #
    #         logger.info(f"batch_files_sender_to_tg: Подготовка группы {current_batch}/{total_batches}")
    #
    #         def main():
    #             file_paths = (
    #                 "students10.txt",
    #                 "students11.txt",
    #                 "students12.txt"
    #             )
    #             # From 2 to 10 items in one media group
    #             # https://core.telegram.org/bots/api#sendmediagroup
    #             media_group = list()
    #             for f in file_paths:
    #                 with open(f, "rb") as fin:
    #                     # Up to 1024 characters.
    #                     # https://core.telegram.org/bots/api#inputmediadocument
    #                     caption = f"Total students in {f}: {len(fin.readlines())}\n"
    #                     # After the len(fin.readlines()) file's current position
    #                     # will be at the end of the file. seek(0) sets the position
    #                     # to the begining of the file so we can read it again during
    #                     # sending.
    #                     fin.seek(0)
    #                     media_group.append(types.FSInputFile(f))
    #
    #             bot.send_media_group(-4221870448, media=media_group)
    #
    #         #     for pdf_path in batch:
    #         #         try:
    #         #             with open(pdf_path, "rb") as fin:
    #         #                 caption = f"Отчет: {Path(pdf_path).name}"
    #         #                 fin.seek(0)
    #         #                 media_group.append(InputMediaDocument(fin, caption=caption))
    #         #                 logger.info(f"batch_files_sender_to_tg: Файл {pdf_path} добавлен в группу")
    #         #         except Exception as e:
    #         #             logger.exception(f"batch_files_sender_to_tg: Ошибка при подготовке файла {pdf_path}: {str(e)}")
    #         #             continue
    #         #
    #         #     if media_group:
    #         #         try:
    #         #             logger.info(f"batch_files_sender_to_tg: Отправка группы {current_batch}/{total_batches} ({len(media_group)} файлов)")
    #         #             bot.send_media_group(CHAT_ID, media=media_group)
    #         #             logger.info(f"batch_files_sender_to_tg: Группа {current_batch}/{total_batches} успешно отправлена")
    #         #         except Exception as e:
    #         #             logger.exception(f"batch_files_sender_to_tg: Ошибка при отправке группы {current_batch}/{total_batches}: {str(e)}")
    #         #     else:
    #         #         logger.warning(f"batch_files_sender_to_tg: Группа {current_batch}/{total_batches} пуста, пропускаем")
    #         #
    #         # logger.info("batch_files_sender_to_tg: Отправка всех файлов завершена")завершена

class BotStatisticsDailyReportClass(PdfReportBaseClass):

    @staticmethod
    @shared_task
    def statistics_sender_main_task():
        avito_accounts = AvitoAccount.objects.all()
        logger.warning(f"statistics_sender_main_task STARTED for {len(avito_accounts)} accounts")
        if ENVIRONMENT == "DEVELOPMENT":
            avito_accounts = AvitoAccount.objects.filter(id=145213826)
        for avito_account in avito_accounts:
            chat_bot_is_active_flag = hasattr(avito_account, "ai_chat_bots") and avito_account.ai_chat_bots.is_active
            need_report_flag = hasattr(avito_account, "ai_chat_bots") and avito_account.ai_chat_bots.statistics_daily_report
            if chat_bot_is_active_flag and need_report_flag:
                logger.warning("processing")
                logger.info(f"need_report_flag - {need_report_flag}")
                if ENVIRONMENT == "DEVELOPMENT":
                    async_to_sync(avito_account.update_refresh_token_async)()
                BotStatisticsDailyReportClass.statistics_sender_small_task.delay(avito_account.id)
            else:
                logger.warning(f"skipped avito_account - {avito_account.name}")
                logger.info(f"chat_bot_is_active_flag - {chat_bot_is_active_flag}")
                logger.info(f"need_report_flag - {need_report_flag}")


    @staticmethod
    @shared_task
    def statistics_sender_small_task(avito_account_id):
        avito_account = AvitoAccount.objects.get(id=avito_account_id)
        statistics = BotStatisticsDailyReportClass.get_raw_data(avito_account)

        # TEXT MESSAGE
        if statistics is not None and statistics.get("bot_chats_count") > 0: #
            BotStatisticsDailyReportClass.statistics_txt_sender_task.delay(str(avito_account.id), statistics)

            # HISTORY PDFs
            need_history_flag = hasattr(avito_account, "ai_chat_bots") and avito_account.ai_chat_bots.histories_for_statistics
            if need_history_flag:
                chats = statistics.get("chats") or None
                if chats:
                    for chat in chats:
                        ChatHistoryReportClass.history_pdf_sender_main_task.delay(avito_account_id=avito_account.id,
                                                                                  chat=chat)
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
            BotStatisticsDailyReportClass.file_sender_to_tg(pdf_path, avito_account.telegram_id)

        #HISTORY
        chats = statistics.get("chats") or None
        if chats:
            for chat in chats:
                ChatHistoryReportClass.history_pdf_sender_main_task.delay(avito_account_id=avito_account.id, chat=chat)

    @staticmethod
    def get_html(statistics):
        with open(f"chat_bot/templates/chat_bot/daily_statistics.html", "r", encoding="utf-8") as file:
            clear_template = file.read()
        template = Template(clear_template)
        avito_account_name = statistics.get('avito_account_name') if statistics else "Неизвестно"
        date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        return template.render(avito_account_name=avito_account_name,start_date=date, statistics=statistics)

    @staticmethod
    @shared_task
    def statistics_txt_sender_task(avito_account_id: str, statistics: dict):
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
    def history_pdf_sender_main_task(avito_account_id, chat, summary_html = None):
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
        logger.info(f"Summary report 1 log info")
        logger.warning(f"Summary report 1 log warning")
        logger.exception(f"Summary report 1 log exception")
        all_tasks = ChatBotTask.objects.filter(chat_id=chat_id)
        if ENVIRONMENT == "PRODUCTION":
            if all_tasks.filter(summary_sanded=True).exists():
                logger.info(f"Summary report already sent for chat_id {chat_id}.")
                return

        avito_account = AvitoAccount.objects.filter(id=avito_account_id).last()
        chat = MessagingAPISync.get_chat_by_id(avito_account, chat_id)
        messages = MessagingAPISync.get_chat_last_50_messages_by_chat_id(avito_account, chat_id)
        chat["messages"] = messages
        if messages is not None and len(messages) > 0:  # skip who can't have bot chats
            chat_summary = chat_summary_ai_generator(avito_account, chat_id)
            logger.info(f"Summary report chat_summary - {chat_summary}.")
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
        summary_text = ChatBotSummaryReportClass.get_chat_summary_text(chat_summary, chat)
        logger.info(f"Summary report summary_text {summary_text}.")
        if summary_text and len(summary_text) > 20:  # 20 is random value)
            ChatBotSummaryReportClass.text_sender_to_tg(text=summary_text, telegram_id=avito_account.telegram_id)
            logger.info(f"Summary report text sended to {avito_account.name} telegram.")

        # PDF FILE
        summary_html = ChatBotSummaryReportClass.get_chat_summary_html(chat_summary, chat)
        ChatHistoryReportClass.history_pdf_sender_main_task.delay(avito_account.id, chat, summary_html)


    @staticmethod
    def get_chat_summary_html(chat_summary, chat):
        counter = 1
        text = "<div style='font-family: Arial, sans-serif;'><b>Сводка по переписке:</b><br><br>"

        title = chat.get("context").get("value").get("title")
        city_name_from_item = chat.get("context").get("value").get("location").get("title") or None

        if title:
            text += f"<p style='margin-left: 20px;'>{counter}. Название объявления: {title}</p>"
            counter += 1

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
        city_name_from_item = chat.get("context").get("value").get("location").get("title") or None

        if title:
            text += f"🔹 {counter}. Название объявления: {title}\n"
            counter += 1

        if city_name_from_item:
            text += f"🔸 {counter}. <u><b>Город обращения: {city_name_from_item}</b></u> \n"
            counter += 1

        for key, value in chat_summary.get("paragraphs").items():
            text += f"🔹 {counter}. {value} \n"
            counter += 1
        return text




