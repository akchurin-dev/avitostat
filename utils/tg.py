from aiogram.types import FSInputFile
from pathlib import Path
from telegram_bot import bot


def send_document(chat_id: str | int, path: Path | str) -> None:
    # async_to_sync(asend_document)(chat_id, path)
    bot.send_raw(
        chat_id=chat_id,
        function="send_document",
        document=FSInputFile(path),
    )


# async def asend_document(chat_id: str | int, path: Path | str) -> None:
#     await bot.bot.session.close()
#     await bot.bot.send_document(
#         chat_id=chat_id,
#         document=FSInputFile(path),
#     )


def send_message(chat_id: str | int, text: str) -> None:
    # async_to_sync(asend_message)(chat_id, text)
    bot.send_raw(
        chat_id=chat_id,
        function="send_message",
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# async def asend_message(chat_id: str | int, text: str) -> None:
#     await bot.bot.session.close()
#     await bot.bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
