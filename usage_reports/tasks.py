from datetime import datetime
from datetime import timedelta
from typing import TypedDict

from aiogram import Bot
from aiogram.enums import ParseMode
from asgiref.sync import async_to_sync
from celery import shared_task
from django.db.models import ExpressionWrapper
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import Sum

from ai_requests.models import AIRequest
from base.settings import AVITOSTATA_ALIVE_BOT_TOKEN
from base.settings import AVITOSTATA_ALIVE_REPORTS_CHAT_ID
from chat_bot.models import ChatBotTask
from utils.logging import TraceLogger


class BaseTokenUsage(TypedDict):
    tokens_prompt: int
    tokens_completion: int
    total_tokens: int


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
    stats: list[TokenUsageByAvitoAccount] = list(
        ChatBotTask.objects
        .filter(created_at__gte=since, created_at__lt=until)
        .values('avito_account__id', 'avito_account__name')
        .annotate(
            total_prompt=Sum('tokens_prompt'),
            total_completion=Sum('tokens_completion'),
        )
        .annotate(
            total_tokens=ExpressionWrapper(
                F('total_prompt') + F('total_completion'),
                output_field=IntegerField()
            )
        )
        .order_by('-total_tokens')
    )

    tlogger.info(f"Token usage by avito accounts report between {since.isoformat()} and {until.isoformat()}:")
    for stat in stats:
        tlogger.info(f"Avito Account: {stat['avito_account__name']} (ID: {stat['avito_account__id']})")
        tlogger.info(f"  Tokens Prompt: {stat['total_prompt'] or 0}")
        tlogger.info(f"  Tokens Completion: {stat['total_completion'] or 0}")
        tlogger.info(f"  Total Tokens: {stat['total_tokens'] or 0}")
        tlogger.info("-" * 40)

    return stats


def get_usage_by_models(since: datetime, until: datetime, *, tlogger: TraceLogger) -> list[TokenUsageByModel]:
    stats: list[TokenUsageByModel] = list(
        AIRequest.objects.filter(
            created_at__gte=since, created_at__lt=until,
        )
        .values('model')
        .annotate(
            tokens_prompt=Sum('tokens_prompt'),
            tokens_completion=Sum('tokens_completion'),
        )
        .annotate(
            total_tokens=ExpressionWrapper(
                F('tokens_prompt') + F('tokens_completion'),
                output_field=IntegerField()
            )
        )
        .order_by('-total_tokens')
    )

    tlogger.info(f"Token usage by gpt models report between {since.isoformat()} and {until.isoformat()}")
    for stat in stats:
        tlogger.info("Model: " + stat["model"])
        tlogger.info(f"   Tokens Prompt: {stat["tokens_prompt"] or 0}")
        tlogger.info(f"   Tokens Completion: {stat["tokens_completion"] or 0}")
        tlogger.info(f"  Total Tokens: {stat["total_tokens"] or 0}")

    return stats


def send_stats_to_tg(usages_by_models: list[TokenUsageByModel], usages_by_avito_accounts: list[TokenUsageByAvitoAccount]) -> None:
    async def f() -> None:
        async with Bot(AVITOSTATA_ALIVE_BOT_TOKEN) as bot:
            text1 = "\n\n".join([
                "\n".join([
                    f"Модель: {usage_by_model["model"]}",
                    f"    Токены на промпт: {usage_by_model["tokens_prompt"]}",
                    f"    Токены на выполнение: {usage_by_model["tokens_completion"]}",
                    f"    Токенов всего: {usage_by_model["total_tokens"]}",
                ]) for usage_by_model in usages_by_models
            ])

            text2 = "\n\n".join([
                "\n".join([
                    f"Авито-аккаунт: {usage_by_avito_account["avito_account__name"]}",
                    f"    Токены на промпт: {usage_by_avito_account["tokens_prompt"]}",
                    f"    Токены на выполнение: {usage_by_avito_account["tokens_completion"]}",
                    f"    Токенов всего: {usage_by_avito_account["total_tokens"]}",
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
