import datetime
import sentry_sdk
from aiogram import Bot
from asgiref.sync import sync_to_async
from telegram_bot import bot
from avito_account.models.models import AvitoAccount
from base import settings
from conversion.utils_week_report import get_text_statistics_report
from base.exceptions import HTTPException
from messaging.bad_mes_report.statistics.total_statistics_utils import get_duration_statistics
from messaging.bad_mes_report.utils_chats import get_ready_chats
from messaging.utils_duration import get_durations_seconds


async def get_all_telegram_ids():
    avito_accounts = await sync_to_async(list)(AvitoAccount.objects.all())
    avito_account_ids = [avito_account.telegram_id for avito_account in avito_accounts if
                         avito_account.telegram_id]
    unique_avito_account_ids = list(set(avito_account_ids))
    if unique_avito_account_ids:
        return unique_avito_account_ids
    else:
        raise HTTPException(status_code=404, detail="Not found any Avito accounts")


async def get_week_report_by_avito_id(avito_id: int):
    avito_account = await sync_to_async(AvitoAccount.objects.filter(id=avito_id).last)()
    if avito_account:
        # await avito_account.update_refresh_token_async()
        try:
            week_report = await get_text_statistics_report(avito_account=avito_account)
            return week_report
        except HTTPException as e:
            raise HTTPException(status_code=404, detail=e.detail)
    else:
        raise HTTPException(status_code=404, detail="Avito account not found")


async def get_duration_report_by_avito_id(avito_id):
    avito_account = await sync_to_async(AvitoAccount.objects.filter(id=avito_id).last)()

    if avito_account:
        ready_chats, chats_without_filtering_count = await get_ready_chats(avito_account)
        if len(ready_chats) > 1:
            #PROCESSING WITH FILTERED CHATS
            durations = await get_durations_seconds(ready_chats)
            duration_statistics = await get_duration_statistics(durations)
            return duration_statistics
        else:
            raise HTTPException(status_code=404, detail="Чаты не найдены")
    else:
        raise HTTPException(status_code=404, detail="Авито аккаунт не найден")


async def handle_avito_account_not_found(telegram_chat_id: str, bot: Bot):
    await bot.send_message(
        chat_id=telegram_chat_id,
        text=(
            "⚠️ Ошибка: Ваша телеграм группа не найдена.\n"
            "🛠️ Пожалуйста, проверьте настройки и повторите попытку."
        )
    )
    raise HTTPException(status_code=404, detail="Avito account not found")


async def handle_avito_account_have_not_active_items_for_period(telegram_chat_id: str, bot: Bot):
    await bot.send_message(
        chat_id=telegram_chat_id,
        text=(
            "⚠️ Ошибка: Для данного Авито аккаунта нет активных объявлений за отчётный период \n"
        )
    )
    raise HTTPException(status_code=404, detail="Avito account does not have active items in period")


async def generate_week_report_text(week_report_data):
    date_from = week_report_data.get("period").get("date_from")
    date_to = week_report_data.get("period").get("date_to")
    avito_account_name = week_report_data.get("avito_account_name")
    active_items_count = week_report_data.get("total_metrics").get("total_items_count").get("active")
    visited_items_count = week_report_data.get("total_metrics").get("total_items_count").get("visited")
    total_contacts_count = week_report_data.get("total_metrics").get("total_contacts_count")
    total_views_count = week_report_data.get("total_metrics").get("total_views_count")
    total_coast = week_report_data.get("total_metrics").get("total_coast")
    total_coast_per_contact = week_report_data.get("total_metrics").get("total_coast_per_contact")

    if week_report_data.get("chat_bot") is not None:
        chat_bot_chats_count = week_report_data.get("chat_bot").get("chats_count", 0)
        chat_bot_messages_count = week_report_data.get("chat_bot").get("messages_count", 0)
        chat_bot_contacts_count = week_report_data.get("chat_bot").get("contacts_count", 0)
    # else:
    #     chat_bot_chats_count, chat_bot_messages_count, chat_bot_contacts_count = ["не подключено 🥺" for i in range(3)]

    date_from = datetime.datetime.strptime(date_from, "%Y-%m-%d").strftime("%d-%m-%Y")
    date_to = datetime.datetime.strptime(date_to, "%Y-%m-%d").strftime("%d-%m-%Y")

    text = (f"\n<><><><><><><><><><><><><><><><><><>\n"
            f"\n      📊 *Еженедельный отчёт* 📅\n\n"
            f"📅 *Период:* с {date_from} по {date_to}\n"
            f"👤 *Аккаунт:* {avito_account_name}\n"
            f"📋 *Активных объявлений:* {active_items_count}\n"
            f"📈 *Посещено объявлений:* {visited_items_count}\n"
            f"📞 *Запрошено контактов:* {total_contacts_count}\n"
            f"👁️ *Просмотров:* {total_views_count}\n"
            f"💸 *Затраты:* {round(total_coast, 2)} р\n"
            f"💰 *Цена за контакт:* {round(total_coast_per_contact, 2)} р\n\n")

    if chat_bot_chats_count or chat_bot_messages_count or chat_bot_contacts_count:
        text += (
            f"\n<><><><><><><><><><><><><><><><><><>\n"
            f"\n\n    🤖 *Чат-бот* \n\n"
            f"🔹 Полученных контактов: {chat_bot_contacts_count} \n"
            f"🔸 Переписок чат-бота: {chat_bot_chats_count} \n"
            f"🔸 Сообщений от чат-бота: {chat_bot_messages_count} \n"
        )

    text += await generate_top_items_text(week_report_data.get("top"))
    return text


async def generate_top_items_text(top_items):
    statistics_total = (f"\n<><><><><><><><><><><><><><><><><><>\n"
                        "\n\n    🏆 *Топовые объявления*\n")
    if top_items is not None:
        for item, item_data in top_items.items():
            statistics_total += (f"\n📢 *Объявление №{item}*\n"
                                 f"🔹 *Название:* {item_data.get('itemTitle', 'Без названия')}\n"
                                 f"🔸 *Запрошен контакт:* {item_data.get('uniqContacts', 0)}\n"
                                 f"🔸 *Просмотры:* {item_data.get('uniqViews', 0)}\n"
                                 f"🔸 *Затраты:* {round(item_data.get('coast', 0), 2)} р\n"
                                 f"🔸 *Цена за контакт:* {round(item_data.get('amount_per_contact', 0), 2)} р\n"
                                 f"🔸 *Цена за просмотр:* {round(item_data.get('amount_per_view', 0), 2)} р\n")
    return statistics_total


async def generate_duration_report_text(duration_report_data):
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


async def get_week_report_text(avito_account: AvitoAccount):
    avito_id = avito_account.id
    telegram_chat_id = avito_account.telegram_id

    try:
        if settings.ENVIRONMENT == 'DEVELOPMENT':
            await sync_to_async(bot.send_raw, thread_sensitive=False)(
                chat_id="-4221870448",
                function="send_message",
                text="📊 Ожидайте, формируется отчёт...",
            )

        week_report_data = await get_week_report_by_avito_id(avito_id=avito_id)
        if week_report_data.get("error") == "Avito account not found":
            await handle_avito_account_not_found(telegram_chat_id, bot)
            return
        elif week_report_data.get("error") == "Avito account does not have active items in period":
            await handle_avito_account_have_not_active_items_for_period(telegram_chat_id, bot)
            return

        report_text = await generate_week_report_text(week_report_data)

        duration_report_data = await get_duration_report_by_avito_id(avito_id=avito_id)
        if duration_report_data:
            report_text += await generate_duration_report_text(duration_report_data)

        return report_text
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise
