import datetime

from asgiref.sync import async_to_sync
from celery import shared_task
from django.db.models import Q
from django.utils import timezone
from pydantic import BaseModel

import messaging.api
from avito_account.models.models import AvitoAccount
from chat_bot.models import AiChatBot
from chat_bot.models import ChatBotTask
from chat_bot.models import CompanyBranch
from chat_bot.utils import history_pdf
from messaging.bad_mes_report.utils_chats import filter_by_bot_answered_chat_ids
from messaging.bad_mes_report.utils_chats import filter_chats_for_last_period
from messaging.bad_mes_report.utils_chats import filter_chats_only_with_text
from utils import tg
from utils.logging import TraceLogger


class Statistic(BaseModel):
        avito_account_id: int
        avito_account_name: str | None
        company_branch_location: str | None = None
        total_chats_count: int
        bot_chats_count: int
        contacts_count: int
        chats: list[messaging.api.Chat]
        bot_answered_mes_ids: list[str]
        chats_with_contacts_ids: list[str]


@shared_task
def statistics_for_avito_account(account_id: int, *, trace_id: str | None = None):
    tlogger = TraceLogger(trace_id)

    account = AvitoAccount.objects.get(pk=account_id)
    aichatbot = AiChatBot.objects.filter(account=account).first()

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
        statistics_for_company_branch.delay(account.pk, company_branch_id)

    tlogger.info(f"Daily report launched for {len(company_branches_id)} branches of {account.name}")


@shared_task
def statistics_for_company_branch(avito_account_id: int, company_branch_id: int | None):
    tlogger = TraceLogger()

    avito_account = AvitoAccount.objects.get(id=avito_account_id)

    company_branch = None
    if company_branch_id:
        company_branch = CompanyBranch.objects.get(pk=company_branch_id)

    tlogger.info(f"Daily report for '{company_branch}' branch of '{avito_account.name}'")

    statistics = get_raw_data(avito_account, company_branch, tlogger=tlogger)

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

    statistics_txt_sender(telegram_id, statistics)
    history_main_sender(avito_account, telegram_id, statistics, tlogger=tlogger)

    tlogger.info("Finished successfully")


def get_raw_data(
    avito_account: AvitoAccount,
    company_branch: CompanyBranch | None,
    period="day",
    *,
    tlogger: TraceLogger,
) -> Statistic | None:

    chats = list(messaging.api.get_chats(avito_account, period=period))

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
    actual_chats = filter_chats_for_last_period(chats, period=period)
    actual_chats_with_mes = messaging.api.get_chats_last_50_messages(avito_account, actual_chats, tlogger=tlogger)
    only_with_text = filter_chats_only_with_text(actual_chats_with_mes)
    bot_chats_with_messages = filter_by_bot_answered_chat_ids(only_with_text, unique_bot_chat_ids)

    return Statistic(
        avito_account_id=avito_account.pk,
        avito_account_name=avito_account.name,
        company_branch_location=company_branch.location if company_branch else None,
        total_chats_count=len(only_with_text),
        bot_chats_count=len(bot_chats_with_messages),
        contacts_count=contacts_count,
        chats=bot_chats_with_messages,
        bot_answered_mes_ids=bot_answered_mes_ids,
        chats_with_contacts_ids=list(tasks_with_contact.values_list("chat_id", flat=True)),
    )


def statistics_txt_sender(telegram_id: str, statistics: Statistic):
    #STATISTICS
    tomorrow = (datetime.datetime.now().date()-datetime.timedelta(days=1)).strftime("%d.%m.%Y")

    avito_account_name = statistics.avito_account_name
    total_chats_count = statistics.total_chats_count
    bot_chats_count = statistics.bot_chats_count
    contacts_count = statistics.contacts_count

    lines = [
        f"📈 <b>Статистика переписок бота за {tomorrow}</b> 📅",
        "",
        f"👤 <b>Ваш Аккаунт:</b> <code> {avito_account_name}</code>",
    ]

    if statistics.company_branch_location:
        lines.append(f"📍 <b>Город:</b> <code> {statistics.company_branch_location}</code>")

    lines.extend([
        f"💬 <b>Всего чатов:</b> <code> {total_chats_count}</code>",
        f"🤖 <b>Чатов с ботом:</b> <code> {bot_chats_count}</code>",
        f"🎉 <b>Получено контактов:</b> <code> {contacts_count}</code>",
        f"📭 <b>Чатов без контактов:</b> <code> {bot_chats_count - contacts_count}</code>"
    ])

    text = "\n".join(lines)
    # BotStatisticsDailyReportClass.text_sender_to_tg(text, telegram_id)
    tg.send_message(telegram_id, text)


def history_main_sender(avito_account: AvitoAccount, telegram_id: str, statistics: Statistic, *, tlogger: TraceLogger):
    chats_with_contacts_ids = statistics.chats_with_contacts_ids

    aichatbot: AiChatBot | None = AiChatBot.objects.filter(account=avito_account).first()

    if aichatbot is None:
        tlogger.info(f"Stop history sending for '{avito_account.name}'. AiChatBot is None")
        return

    if not aichatbot.histories_closed and not aichatbot.histories_open:
        tlogger.info(f"Stop history sending for '{avito_account.name}'. histories_closed and histories_open are both disabled")
        return

    chats = statistics.chats
    have_closed_chats = len(chats_with_contacts_ids) > 0
    have_open_chats = (len(chats) - len(chats_with_contacts_ids)) > 0

    chats = statistics.chats or []

    if len(chats) != 0 and have_closed_chats and aichatbot.histories_closed:
        message_title = f"✅ <b>История закрытых переписок ({len(chats_with_contacts_ids)} шт) :</b>"
        # PdfReportBaseClass.text_sender_to_tg(f"✅ <b>История закрытых переписок"
        #                                         f" ({len(chats_with_contacts_ids)} шт) :</b>",
        #                                         telegram_id)
        tg.send_message(telegram_id, message_title)
        for chat in chats:
            if chat.get("id") in chats_with_contacts_ids:  # ДУМАЮ МОЖНО УБРАТЬ, НО НАДО ПРОВЕРЯТЬ
                history_pdf.history_pdf_sender_task(
                    avito_account_id=avito_account.pk,
                    chat=chat,
                    telegram_id=telegram_id,
                )

    if chats and have_open_chats and aichatbot.histories_open:
        message_title = f"❌ <b>История НЕ закрытых переписок ({len(chats) - len(chats_with_contacts_ids)} шт)  :</b>"
        # PdfReportBaseClass.text_sender_to_tg(f"❌ <b>История НЕ закрытых переписок"
        #                                         f" ({len(chats) - len(chats_with_contacts_ids)} шт)  :</b>",
        #                                         telegram_id)
        tg.send_message(telegram_id, message_title)
        for chat in chats:
            if chat.get("id") not in chats_with_contacts_ids:
                history_pdf.history_pdf_sender_task(
                    avito_account_id=avito_account.pk,
                    chat=chat,
                    telegram_id=telegram_id,
                )
