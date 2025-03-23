from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from asgiref.sync import async_to_sync

from tests import config


bot_checker = Bot(
    token=config.TELEGRAM_BOT_TOKEN,
)

_summary_sender_bot_id: int | None = None


def get_new_messages_in_summary_chat(last_message_id: int) -> list[Message]:
    async def f() -> list[Message]:
        await bot_checker.session.close()

        messages: list[Message] = []
        message_id = await aget_last_message_id()

        while message_id > last_message_id:
            message = await aread_message(message_id)

            if message:
                messages.append(message)

            message_id -= 1

        return messages

    return async_to_sync(f)()


def summary_sender_bot_id() -> int:
    global _summary_sender_bot_id

    if _summary_sender_bot_id:
        return _summary_sender_bot_id

    async def f():
        async with Bot(token=config.TELEGRAM_BOT_TOKEN) as summary_sender_bot:
            bot_info = await summary_sender_bot.get_me()

        return bot_info.id

    _summary_sender_bot_id = async_to_sync(f)()

    return _summary_sender_bot_id


async def aget_last_message_id():
    temp_msg = await bot_checker.send_message(
        chat_id=config.SUMMARY_CHAT_ID,
        text='.',
        disable_notification=True,
    )
    msg_id = temp_msg.message_id
    await temp_msg.delete()
    return msg_id


def get_last_message_id():
    reset_bot_checker()
    return async_to_sync(aget_last_message_id)()


async def aread_message(message_id: int) -> Message | None:
    try:
        temp_msg = await bot_checker.send_message(
            chat_id=config.SUMMARY_CHAT_ID,
            text='.',
            reply_to_message_id=message_id,
            disable_notification=True,
        )
        msg = temp_msg.reply_to_message
        await temp_msg.delete()
    except TelegramBadRequest:
        return None

    return msg


def reset_bot_checker():
    async_to_sync(bot_checker.session.close)()
