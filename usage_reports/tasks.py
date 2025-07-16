from datetime import datetime
from datetime import timedelta
from typing import TypedDict

from aiogram import Bot
from aiogram.enums import ParseMode
from asgiref.sync import async_to_sync
from celery import shared_task
from django.db.models import Avg
from django.db.models import Count
from django.db.models import Sum
from django.db.models.functions import Round

from ai_requests.models import AIRequest
from base.settings import AVITOSTATA_ALIVE_BOT_TOKEN
from base.settings import AVITOSTATA_ALIVE_REPORTS_CHAT_ID
from chat_bot.models import ChatBotTask
from utils.logging import TraceLogger


class BaseTokenUsage(TypedDict):
    count: int
    avg_prompt: float
    sum_prompt: int
    avg_completion: float
    sum_completion: int


class TokenUsageByModel(BaseTokenUsage):
    model: str


class TokenUsageByAvitoAccount(BaseTokenUsage):
    avito_account__id: int
    avito_account__name: str


@shared_task
def report_daily_token_usage():
    tlogger = TraceLogger()
    tlogger.info("Daily report started")

    end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=1)

    usage_by_models = get_usage_by_models(start, end, tlogger=tlogger)
    usage_by_avito_accounts = get_usage_by_avito_accounts(start, end, tlogger=tlogger)

    send_stats_to_tg(usage_by_models, usage_by_avito_accounts)


def get_usage_by_avito_accounts(since: datetime, until: datetime, *, tlogger: TraceLogger) -> list[TokenUsageByAvitoAccount]:
    stats: list[TokenUsageByAvitoAccount] = list(_add_annotation(
        ChatBotTask.objects
        .filter(created_at__gte=since, created_at__lt=until)
        .values('avito_account__id', 'avito_account__name')
    ))

    tlogger.info(f"Token usage by avito accounts report between {since.isoformat()} and {until.isoformat()}:")
    for stat in stats:
        tlogger.info(f"Avito Account: {stat['avito_account__name']} (ID: {stat['avito_account__id']})")
        _log_annotations_and_delimeter(stat, tlogger=tlogger)

    return stats


def get_usage_by_models(since: datetime, until: datetime, *, tlogger: TraceLogger) -> list[TokenUsageByModel]:
    stats: list[TokenUsageByModel] = list(_add_annotation(
        AIRequest.objects.filter(
            created_at__gte=since, created_at__lt=until,
        )
        .values('model')
    ))

    tlogger.info(f"Token usage by gpt models report between {since.isoformat()} and {until.isoformat()}")
    for stat in stats:
        tlogger.info("Model: " + stat['model'])
        _log_annotations_and_delimeter(stat, tlogger=tlogger)

    return stats


def send_stats_to_tg(usages_by_models: list[TokenUsageByModel], usages_by_avito_accounts: list[TokenUsageByAvitoAccount]) -> None:
    async def f() -> None:
        async with Bot(AVITOSTATA_ALIVE_BOT_TOKEN) as bot:
            text1 = "\n\n".join([
                "\n".join([
                    f"Модель: {usage_by_model['model']}",
                    f"    Запросов: {usage_by_model['count']}",
                    f"    В среднем токенов на промпт: {usage_by_model['avg_prompt']}",
                    f"    Всего токенов на промпт: {usage_by_model['sum_prompt']}",
                    f"    В среднем токенов на выполнение: {usage_by_model['avg_completion']}",
                    f"    Всего токенов на выполнение: {usage_by_model['sum_completion']}",
                ]) for usage_by_model in usages_by_models
            ])

            text2 = "\n\n".join([
                "\n".join([
                    f"Авито-аккаунт: {usage_by_avito_account['avito_account__name']}",
                    f"    Сообщений обработано: {usage_by_avito_account['count']}",
                    f"    В среднем токенов на промпт: {usage_by_avito_account['avg_prompt']}",
                    f"    Всего токенов на промпт: {usage_by_avito_account['sum_prompt']}",
                    f"    В среднем токенов на выполнение: {usage_by_avito_account['avg_completion']}",
                    f"    Всего токенов на выполнение: {usage_by_avito_account['sum_completion']}",
                ]) for usage_by_avito_account in usages_by_avito_accounts
            ])

            await send_message(bot, text1)
            await send_message(bot, text2)

    async_to_sync(f)()


async def send_message(bot: Bot, text: str) -> None:
    while text:
        text_part = text[:4000]
        await bot.send_message(AVITOSTATA_ALIVE_REPORTS_CHAT_ID, text_part, parse_mode=ParseMode.HTML)
        text = text[len(text_part):]


def _add_annotation(qs) -> list:
    return qs.annotate(
        count=Count('*'),
        avg_prompt=Round(Avg('tokens_prompt'), 2),
        sum_prompt=Sum('tokens_prompt'),
        avg_completion=Round(Avg('tokens_completion'), 2),
        sum_completion=Sum('tokens_completion'),
    ).order_by('-count')


def _log_annotations_and_delimeter(stat: BaseTokenUsage, *, tlogger: TraceLogger) -> None:
    tlogger.info(f"  Records Count: {stat['count']}")
    tlogger.info(f"  Avg Prompt Tokens: {stat['avg_prompt']}")
    tlogger.info(f"  Sum Prompt Tokens: {stat['sum_prompt']}")
    tlogger.info(f"  Avg Completion Tokens: {stat['avg_completion']}")
    tlogger.info(f"  Sum Completion Tokens: {stat['sum_completion']}")
    tlogger.info("-" * 40)
