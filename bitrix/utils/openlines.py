import asyncio
import pprint

from loguru import logger
import pydantic

from bitrix.utils import bitrix_api
from bitrix.utils import bitrix_bots


class Openline(pydantic.BaseModel):
    ID: int


async def activate_bot(bitrix_domain: str):
    """ Включает бота во все открытые линии в домене """

    openlines = await get_openlines(bitrix_domain)
    bot_id = await bitrix_bots.get_bitrix_bot_id(bitrix_domain)

    async with asyncio.TaskGroup() as task_group:
        for openline in openlines:
            task_group.create_task(enable_bot_in_openline(bitrix_domain, openline.ID, bot_id))


async def disable_bot(bitrix_domain: str):
    """ Отключает бота во всех открытых линиях """

    openlines = await get_openlines(bitrix_domain)

    async with asyncio.TaskGroup() as task_group:
        for openline in openlines:
            task_group.create_task(disable_bot_in_openline(bitrix_domain, openline.ID))


async def get_openlines(bitrix_domain: str) -> list[Openline]:
    """ https://apidocs.bitrix24.ru/api-reference/imopenlines/openlines/imopenlines-config-list-get.html """

    response = await bitrix_api.get(bitrix_domain, "imopenlines.config.list.get")
    response.raise_for_status()

    data = response.json()
    return [Openline.model_validate(openline) for openline in data["result"]]


async def enable_bot_in_openline(bitrix_domain: str, openline_id: int, bot_id: int):
    return await edit_openline(
        bitrix_domain=bitrix_domain,
        openline_id=openline_id,
        WELCOME_BOT_ENABLE="Y",
        WELCOME_BOT_JOIN="always",
        WELCOME_BOT_ID=bot_id,
        WELCOME_BOT_TIME="0",
        WELCOME_BOT_LEFT="queue"
    )


async def disable_bot_in_openline(bitrix_domain: str, openline_id: int):
    return await edit_openline(
        bitrix_domain=bitrix_domain,
        openline_id=openline_id,
        WELCOME_BOT_ENABLE="N",
    )


async def edit_openline(bitrix_domain: str, openline_id: int, **kwargs):
    """ https://apidocs.bitrix24.ru/api-reference/imopenlines/openlines/imopenlines-config-update.html """

    data = {
        "CONFIG_ID": openline_id,
        "PARAMS": kwargs,
    }

    response = await bitrix_api.post(bitrix_domain, operation="imopenlines.config.update", json=data)
    response.raise_for_status()


async def redirect_client_to_manager(bitrix_domain: str, dialog_id: int):
    """ https://apidocs.bitrix24.ru/api-reference/imopenlines/openlines/chat-bots/imopenlines-bot-session-operator.html """

    response = await bitrix_api.post(
        bitrix_domain=bitrix_domain,
        operation="imopenlines.bot.session.operator",
        json={
            "CHAT_ID": dialog_id,
        },
    )
    response.raise_for_status()
