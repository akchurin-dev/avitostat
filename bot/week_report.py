from aiogram.exceptions import AiogramError
from aiogram.types import Message
from telegram_bot.api.week_report import get_week_report_by_telegram_id, get_duration_report_by_telegram_id


async def get_week_report_text(message: Message):
    await message.answer("📊 Ожидайте, формируется отчёт...")

    week_report_data = get_week_report_by_telegram_id(telegram_chat_id=message.chat.id)
    if week_report_data.get("error") == "Avito account not found":
        await handle_avito_account_not_found(message)
        return

    report_text = generate_week_report_text(week_report_data)

    duration_report_data = get_duration_report_by_telegram_id(telegram_chat_id=message.chat.id)
    if duration_report_data:
        report_text += generate_duration_report_text(duration_report_data)

    await message.answer(report_text, parse_mode="Markdown", disable_web_page_preview=True)


async def handle_avito_account_not_found(message: Message):
    await message.answer(
        "⚠️ Ошибка: Ваша телеграм группа не найдена.\n"
        "🛠️ Пожалуйста, проверьте настройки и повторите попытку."
    )
    raise AiogramError("Avito account not found")


def generate_week_report_text(week_report_data):
    avito_account_name = week_report_data.get("avito_account_name")
    total_items_count = week_report_data.get("total_metrics").get("total_items_count").get("active")
    total_contacts_count = week_report_data.get("total_metrics").get("total_contacts_count")
    total_views_count = week_report_data.get("total_metrics").get("total_views_count")
    total_favorites_count = week_report_data.get("total_metrics").get("total_favorites_count")
    total_coast = week_report_data.get("total_metrics").get("total_coast")
    total_coast_per_contact = week_report_data.get("total_metrics").get("total_coast_per_contact")

    text = (f"📅 *Еженедельный отчёт* 📅\n\n"
            f"👤 *Аккаунт:* {avito_account_name}\n"
            f"📋 *Активных объявлений:* {total_items_count}\n"
            f"📞 *Запрошено контактов:* {total_contacts_count}\n"
            f"👁️ *Просмотров:* {total_views_count}\n"
            f"⭐ *В Избранное:* {total_favorites_count}\n"
            f"💸 *Затраты:* {total_coast}\n"
            f"💰 *Цена за контакт:* {total_coast_per_contact}\n\n")

    text += generate_top_items_text(week_report_data.get("top"))
    return text


def generate_top_items_text(top_items):
    statistics_total = ""
    if top_items is not None:
        for item, item_data in top_items.items():
            statistics_total += (f"\n📢 *Объявление №{item}*\n"
                                 f"🔹 *Название:* {item_data.get('itemTitle', 'Без названия')}\n"
                                 f"🔸 *Запрошен контакт:* {item_data.get('uniqContacts', 0)}\n"
                                 f"🔸 *Добавлено в избранные:* {item_data.get('uniqFavorites', 0)}\n"
                                 f"🔸 *Просмотры:* {item_data.get('uniqViews', 0)}\n"
                                 f"🔸 *Затраты:* {item_data.get('coast', 0)}\n"
                                 f"🔸 *Цена за контакт:* {item_data.get('amount_per_contact', 0)}\n"
                                 f"🔸 *Цена за просмотр:* {item_data.get('amount_per_view', 0)}\n")
    return statistics_total


def generate_duration_report_text(duration_report_data):
    duration_report_text = (f"\n⏱ *Среднее время ответа:* \n"
                            f"        {duration_report_data.get('average_duration')}\n"
                            f"⏳ *Топ долгих ответов:*\n")
    for duration in duration_report_data.get("top_durations", []):
        url = f"https://www.avito.ru/profile/messenger/channel/{duration[1]}"
        duration_report_text += f"        📌[{duration[0]}]({url})\n"
    return duration_report_text
