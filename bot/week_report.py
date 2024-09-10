import os
from datetime import datetime

import sentry_sdk
from aiogram import Bot
from aiogram.exceptions import AiogramError
from dotenv import load_dotenv

from tg_bot.api.week_report import get_week_report_by_avito_id, get_duration_report_by_avito_id, \
    get_avito_ids_by_telegram_id


async def get_week_report_text(telegram_chat_id: int, bot: Bot):
    avito_ids = get_avito_ids_by_telegram_id(telegram_chat_id)
    if avito_ids:
        for avito_id in avito_ids:
            load_dotenv()
            ENVIRONMENT = os.getenv('ENVIRONMENT')

            try:
                if ENVIRONMENT == 'DEVELOPMENT':
                    await bot.send_message(
                        chat_id="-4221870448",
                        text="📊 Ожидайте, формируется отчёт..."
                    )

                week_report_data = get_week_report_by_avito_id(avito_id=avito_id)
                if week_report_data.get("error") == "Avito account not found":
                    await handle_avito_account_not_found(telegram_chat_id, bot)
                    return
                elif week_report_data.get("error") == "Avito account does not have active items in period":
                    await handle_avito_account_have_not_active_items_for_period(telegram_chat_id, bot)
                    return

                report_text = generate_week_report_text(week_report_data)

                duration_report_data = get_duration_report_by_avito_id(avito_id=avito_id)
                if duration_report_data:
                    report_text += generate_duration_report_text(duration_report_data)

                return report_text
            except Exception as e:
                sentry_sdk.capture_exception(e)
                print(f"Account_id: {avito_id}\n"
                      f"Exception occurred: {e}")


async def handle_avito_account_not_found(telegram_chat_id: int, bot: Bot):
    await bot.send_message(
        chat_id=telegram_chat_id,
        text=(
            "⚠️ Ошибка: Ваша телеграм группа не найдена.\n"
            "🛠️ Пожалуйста, проверьте настройки и повторите попытку."
        )
    )
    raise AiogramError("Avito account not found")


async def handle_avito_account_have_not_active_items_for_period(telegram_chat_id: int, bot: Bot):
    await bot.send_message(
        chat_id=telegram_chat_id,
        text=(
            "⚠️ Ошибка: Для данного Авито аккаунта нет активных объявлений за отчётный период \n"
        )
    )
    raise AiogramError("Avito account does not have active items in period")


def generate_week_report_text(week_report_data):
    date_from = week_report_data.get("period").get("date_from")
    date_to = week_report_data.get("period").get("date_to")
    avito_account_name = week_report_data.get("avito_account_name")
    active_items_count = week_report_data.get("total_metrics").get("total_items_count").get("active")
    visited_items_count = week_report_data.get("total_metrics").get("total_items_count").get("visited")
    total_contacts_count = week_report_data.get("total_metrics").get("total_contacts_count")
    total_views_count = week_report_data.get("total_metrics").get("total_views_count")
    total_coast = week_report_data.get("total_metrics").get("total_coast")
    total_coast_per_contact = week_report_data.get("total_metrics").get("total_coast_per_contact")

    date_from = datetime.strptime(date_from, "%Y-%m-%d").strftime("%d-%m-%Y")
    date_to = datetime.strptime(date_to, "%Y-%m-%d").strftime("%d-%m-%Y")

    text = (f"📊 *Еженедельный отчёт* 📅\n\n"
            f"📅 *Период:* с {date_from} по {date_to}\n"
            f"👤 *Аккаунт:* {avito_account_name}\n"
            f"📋 *Активных объявлений:* {active_items_count}\n"
            f"📈 *Посещено объявлений:* {visited_items_count}\n"
            f"📞 *Запрошено контактов:* {total_contacts_count}\n"
            f"👁️ *Просмотров:* {total_views_count}\n"
            f"💸 *Затраты:* {round(total_coast, 2)} р\n"
            f"💰 *Цена за контакт:* {total_coast_per_contact} р\n\n")

    text += generate_top_items_text(week_report_data.get("top"))
    return text


def generate_top_items_text(top_items):
    statistics_total = "🏆 *Топовые объявления*\n"
    if top_items is not None:
        for item, item_data in top_items.items():
            statistics_total += (f"\n📢 *Объявление №{item}*\n"
                                 f"🔹 *Название:* {item_data.get('itemTitle', 'Без названия')}\n"
                                 f"🔸 *Запрошен контакт:* {item_data.get('uniqContacts', 0)}\n"
                                 f"🔸 *Просмотры:* {item_data.get('uniqViews', 0)}\n"
                                 f"🔸 *Затраты:* {item_data.get('coast', 0)} р\n"
                                 f"🔸 *Цена за контакт:* {item_data.get('amount_per_contact', 0)} р\n"
                                 f"🔸 *Цена за просмотр:* {item_data.get('amount_per_view', 0)} р\n")
    return statistics_total


def generate_duration_report_text(duration_report_data):
    duration_report_text = (f"\n⏱ *Среднее время ответа:* \n"
                            f"        {duration_report_data.get('average_duration')}\n"
                            f"⏳ *Топ долгих ответов:*\n")
    for duration in duration_report_data.get("top_durations", []):
        url = f"https://www.avito.ru/profile/messenger/channel/{duration[1]}"
        manager = ""
        if duration[2] is not None:
            manager = " - " + duration[2]

        duration_report_text += f"        📌[{duration[0]}]({url}){manager}\n"
    return duration_report_text
