from aiogram.exceptions import AiogramError
from aiogram.types import Message
from telegram_bot.api.week_report import get_week_report_by_telegram_id, get_duration_report_by_telegram_id


async def get_week_report_text(message: Message):
    await message.answer(
        "📊 Ожидайте, формируется отчёт..."
    )

    week_report_data = get_week_report_by_telegram_id(telegram_chat_id=message.chat.id)
    if week_report_data.get("error") == "Avito account not found":
        await message.answer(
            "⚠️ Ошибка: Ваша телеграм группа не найдена.\n"
            " 🛠️ Пожалуйста, проверьте настройки и повторите попытку.")
        raise AiogramError("Avito account not found")

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

    statistics_total = ""
    top_items = week_report_data.get("top")
    if top_items is not None:
        for item in top_items:
            item_data = top_items.get(item, {})
            itemTitle = item_data.get("itemTitle", "Без названия")
            uniqContacts = item_data.get("uniqContacts", 0)
            uniqFavorites = item_data.get("uniqFavorites", 0)
            uniqViews = item_data.get("uniqViews", 0)
            coast = item_data.get("coast", 0)
            amount_per_contact = item_data.get("amount_per_contact", 0)
            amount_per_view = item_data.get("amount_per_view", 0)

            statistics_text = (f"\n📢 *Объявление №{item}*\n"
                               f"🔹 *Название:* {itemTitle}\n")

            if uniqContacts > 0:
                statistics_text += f"🔸 *Запрошен контакт:* {uniqContacts}\n"
            if uniqFavorites > 0:
                statistics_text += f"🔸 *Добавлено в избранные:* {uniqFavorites}\n"
            if uniqViews > 0:
                statistics_text += f"🔸 *Просмотры:* {uniqViews}\n"
            if coast > 0:
                statistics_text += f"🔸 *Затраты:* {coast}\n"
            if amount_per_contact > 0:
                statistics_text += f"🔸 *Цена за контакт:* {amount_per_contact}\n"
            if amount_per_view > 0:
                statistics_text += f"🔸 *Цена за просмотр:* {amount_per_view}\n"
            statistics_total += statistics_text

    duration_report_data = get_duration_report_by_telegram_id(telegram_chat_id=message.chat.id)
    if duration_report_data:
        duration_report_text = (f"\n⏱ *Среднее время ответа:* \n"
                                f"        {duration_report_data.get('average_duration')}\n"
                                f"⏳ *Топ долгих ответов:*\n")
        for duration in duration_report_data.get("top_durations", []):
            url = f"https://www.avito.ru/profile/messenger/channel/{duration[1]}"
            duration_report_text += f"        📌[{duration[0]}]({url})\n"
        statistics_total += duration_report_text

    await message.answer(text + statistics_total, parse_mode="Markdown", disable_web_page_preview=True)

