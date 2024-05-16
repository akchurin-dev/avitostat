import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from dotenv import load_dotenv

from telegram_bot.api.week_report import get_week_report_by_telegram_id
from telegram_bot.cleaner.cleaner import Cleaner
from telegram_bot.cleaner.cleaner_middleware import CleanerMiddleware

load_dotenv()
# t.me/avitostata_bot

logging.basicConfig(level=logging.INFO)

router = Router()


async def get_week_report_text(message: Message):
    await message.answer(
        "Ожидайте, формируется отчёт..."
    )

    week_report_data = get_week_report_by_telegram_id(telegram_chat_id=message.chat.id)
    avito_account_name = week_report_data.get("avito_account_name")
    text = (f"Еженедельный отчёт: \n\n"
            f"Аккаунт - <b>{avito_account_name}</b>\n")

    statistics_total = ""
    conversions = week_report_data.get("conversions")
    if conversions is not None:
        for item in conversions:
            itemTitle = conversions.get(item).get("itemTitle", 0)
            uniqContacts = conversions.get(item).get("uniqContacts", 0)
            uniqFavorites = conversions.get(item).get("uniqFavorites", 0)
            uniqViews = conversions.get(item).get("uniqViews", 0)
            coast = conversions.get(item).get("coast", 0)
            amount_per_contact = conversions.get(item).get("amount_per_contact", 0)
            amount_per_view = conversions.get(item).get("amount_per_view", 0)

            statistics_text = (f"\n Объявление №{item}\n"
                               f"Название - {itemTitle}\n")

            if uniqContacts > 0:
                statistics_text += f"Запрошен контакт - {uniqContacts}\n"
            if uniqFavorites > 0:
                statistics_text += f"Доб. в избранные - {uniqFavorites}\n"
            if uniqViews > 0:
                statistics_text += f"Просмотры - {uniqViews}\n"
            if coast > 0:
                statistics_text += f"Затраты - {coast}\n"
            if amount_per_contact > 0:
                statistics_text += f"Цена контакта - {amount_per_contact}\n"
            if amount_per_view > 0:
                statistics_text += f"Цена просмотра - {amount_per_view}\n"

            statistics_total += statistics_text
    return text + statistics_total


@router.message()
async def echo(message: Message, cleaner):
    msg = message.text.lower()
    if msg == "/week@avitostata_bot":
        text = await get_week_report_text(message=message)
        while text:
            await message.answer(text=text[:4000], parse_mode=ParseMode.HTML)
            text = text[4000:]
    elif msg in ["/help@avitostata_bot", "/help", "help"]:
        await message.reply("/help - список команд \n"
                            "/week - еженедельный отчёт \n")
    else:
        pass


async def main() -> None:
    bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
    dp = Dispatcher()

    dp.include_router(router)

    cleaner = Cleaner(limit=100)
    dp.update.middleware(CleanerMiddleware(cleaner))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
