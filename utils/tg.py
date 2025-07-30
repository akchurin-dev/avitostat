from aiogram import Bot
from aiogram.types import FSInputFile
from asgiref.sync import async_to_sync
from pathlib import Path
from telegram_bot import bot


def send_document(chat_id: str | int, path: Path | str, bot: Bot = bot.bot) -> None:
    async_to_sync(asend_document)(chat_id, path, bot=bot)
    # bot.send_raw(
    #     chat_id=chat_id,
    #     function="send_document",
    #     document=FSInputFile(path),
    # )


async def asend_document(chat_id: str | int, path: Path | str, bot: Bot = bot.bot) -> None:
    await bot.session.close()
    await bot.send_document(
        chat_id=chat_id,
        document=FSInputFile(path),
    )
    await bot.session.close()


def send_message(chat_id: str | int, text: str, parse_mode: str = "HTML", bot: Bot = bot.bot) -> None:
    async_to_sync(asend_message)(chat_id, text, parse_mode=parse_mode, bot=bot)
    # while text:
    #     part = text[:4000]
    #     bot.send_raw(
    #         chat_id=chat_id,
    #         function="send_message",
    #         text=part,
    #         parse_mode=parse_mode,
    #         disable_web_page_preview=True,
    #     )
    #     text = text[len(part):]


async def asend_message(chat_id: str | int, text: str, parse_mode: str = "HTML", bot: Bot = bot.bot) -> None:
    await bot.session.close()

    while text:
        part = text[:4000]
        await bot.send_message(
            chat_id=chat_id,
            text=part,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
        text = text[len(part):]

    await bot.session.close()
