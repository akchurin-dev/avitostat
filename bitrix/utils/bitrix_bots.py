import pydantic

from loguru import logger
from typing import Literal

from django.conf import settings

from bitrix.utils import bitrix_api


class BitrixBot(pydantic.BaseModel):
    ID: int
    NAME: str
    CODE: str
    OPENLINE: Literal["Y", "N"]


async def register_bitrix_chat_bot(bitrix_domain: str):
    """ https://apidocs.bitrix24.ru/api-reference/chat-bots/imbot-register.html """
    
    data = {
        "CODE": settings.BITRIX_BOT_CODE,
        "TYPE": "O",
        "EVENT_HANDLER": f"https://{settings.BITRIX_WEBHOOK_HOST}/bitrix/webhook-inbox",
        "PROPERTIES": {
            "NAME": "Bot Testoviy", # TODO дать имя боту
        }
    }

    response = await bitrix_api.post(
        bitrix_domain=bitrix_domain,
        operation="imbot.register",
        json=data,
    )

    if not response.is_success:
        logger.warning(f"Bitrix inner bot registration for domain {bitrix_domain} failed. Status = {response.status_code}, data = {response.json()}")

    response.raise_for_status()


async def get_bitrix_bot_list(bitrix_domain: str):
    """ https://apidocs.bitrix24.ru/api-reference/chat-bots/imbot-bot-list.html """

    operation = "imbot.bot.list"

    response = await bitrix_api.get(bitrix_domain, operation)
    response.raise_for_status()

    data = response.json()
    return [BitrixBot.model_validate(b) for b in data["result"].values()]


async def get_bitrix_bot_id(bitrix_domain: str) -> int:
    bots = await get_bitrix_bot_list(bitrix_domain)

    for bot in bots:
        if bot.CODE == settings.BITRIX_BOT_CODE:
            return bot.ID

    raise Exception(f"Bot not found in domain {bitrix_domain}")
