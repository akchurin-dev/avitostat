from aiogram.types import FSInputFile
from asgiref.sync import async_to_sync
from pathlib import Path
from telegram_bot import bot


def send_document(chat_id: str | int, path: Path | str) -> None:
    async_to_sync(asend_document)(chat_id, path)


async def asend_document(chat_id: str | int, path: Path | str) -> None:
    await bot.bot.session.close()
    await bot.bot.send_document(
        chat_id=chat_id,
        document=FSInputFile(path),
    )
