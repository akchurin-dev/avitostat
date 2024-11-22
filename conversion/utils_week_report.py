from asgiref.sync import sync_to_async
from django.db.models import Q

from avito_account.api.get_operations import get_active_operations_for_period
from avito_account.models.models import AvitoAccount
from base.settings import MOSCOW_TZ
from chat_bot.models import AiChatBot, ChatBotTask
from conversion.api import get_statistics_for_period
import math
from datetime import datetime


async def get_costs_merged(operations) -> dict:
    costs_merged = {}
    if operations:
        for operation in operations:
            itemId = operation.get('itemId')
            coast = costs_merged.get(itemId)
            if coast is None:
                costs_merged[itemId] = operation.get("period_coast")
            else:
                costs_merged[itemId] = coast + operation.get("period_coast")
    return costs_merged


async def get_top_5_items(items_with_metrics):
    sorted_items = sorted(items_with_metrics.items(),
                          key=lambda item: (-item[1]['uniqContacts'], -item[1]['uniqViews']))
    top_5_items = dict(sorted_items[:5])
    return top_5_items


async def get_items_with_metrics(statistics, operations: list, items: list):
    metrics = {}
    costs_merged = await get_costs_merged(operations=operations)
    if statistics:
        for statistic in statistics:
            itemId = statistic.get("itemId", None)
            if itemId:
                item = None
                for item_from_list in items:
                    if item_from_list.get('id') == itemId:
                        item = item_from_list

                conversion_item = metrics.get(itemId, None)
                if conversion_item is None:
                    stats = statistic.get("stats")
                    if stats:
                        metrics[itemId] = {
                            'itemTitle': item.get("title"),
                            'uniqContacts': 0,
                            'uniqFavorites': 0,
                            'uniqViews': 0,
                        }
                        for stat in stats:
                            metrics[itemId]['uniqContacts'] += stat.get("uniqContacts")
                            metrics[itemId]['uniqFavorites'] += stat.get("uniqFavorites")
                            metrics[itemId]['uniqViews'] += stat.get("uniqViews")

                        coast = costs_merged.get(itemId)
                        if coast:
                            uniq_contacts = metrics[itemId].get("uniqContacts")
                            uniq_favorites = metrics[itemId].get("uniqFavorites")
                            uniq_views = metrics[itemId].get("uniqViews")

                            metrics[itemId]["coast"] = coast
                            if uniq_contacts != 0:
                                metrics[itemId]["amount_per_contact"] = math.floor(coast / uniq_contacts)
                            if uniq_favorites != 0:
                                metrics[itemId]["amount_per_favorite"] = math.floor(coast / uniq_favorites)
                            if uniq_views != 0:
                                metrics[itemId]["amount_per_view"] = math.floor(coast / uniq_views)

    return metrics


async def get_total_metrics(items_with_metrics, items: list, statistics: dict):
    total_metrics = {
        "total_items_count": {
            "active": 0,
            "visited": 0,
        },
        "total_contacts_count": 0,
        "total_views_count": 0,
        "total_favorites_count": 0,
        "total_coast": 0,
        "total_coast_per_contact": 0,

    }
    if items:
        total_metrics["total_items_count"] = {
            "active": len(items),
            "visited": len(statistics)
        }

    for item in items_with_metrics.items():
        total_metrics["total_contacts_count"] += item[1].get("uniqContacts", 0)
        total_metrics["total_views_count"] += item[1].get("uniqViews", 0)
        total_metrics["total_favorites_count"] += item[1].get("uniqFavorites", 0)
        total_metrics["total_coast"] += round(item[1].get("coast", 0), 2)

    total_contacts = total_metrics.get("total_contacts_count", 0)
    total_coast = total_metrics.get("total_coast", 0)
    if total_contacts > 0 and total_coast > 0:
        total_metrics["total_coast_per_contact"] = round((total_coast / total_contacts), 2)

    return total_metrics


async def get_chat_bot_statistics(avito_account: AvitoAccount, date_from, date_to) -> dict | None:
    # Локализуем даты
    date_from = MOSCOW_TZ.localize(datetime.strptime(date_from, '%Y-%m-%d'))
    date_to = MOSCOW_TZ.localize(datetime.strptime(date_to, '%Y-%m-%d')).replace(hour=23, minute=59, second=59,
                                                                                 microsecond=999999)

    # Выполняем фильтрацию в QuerySet (синхронный запрос, но без использования list())
    actual_chat_bot_tasks = await sync_to_async(
        lambda: list(ChatBotTask.objects.filter(
            avito_account=avito_account,
            created_at__gt=date_from,
            created_at__lt=date_to,
            tokens_prompt__gt=0
        ))
    )()

    # Если есть записи, собираем статистику
    if actual_chat_bot_tasks:
        # Количество уникальных чатов
        chats_count = await sync_to_async(lambda: len(set(task.chat_id for task in actual_chat_bot_tasks)))()

        # Общее количество сообщений
        messages_count = await sync_to_async(lambda: len(actual_chat_bot_tasks))()

        # Количество записей с контактами
        contacts_count = await sync_to_async(
            lambda: len([
                task for task in actual_chat_bot_tasks if
                task.address or task.mobile or task.whatsapp or task.telegram or task.email
            ])
        )()

        return {
            "chats_count": chats_count,
            "messages_count": messages_count,
            "contacts_count": contacts_count
        }


async def get_text_statistics_report(avito_account: AvitoAccount):
    metrics = {}
    statistics, items, date_from, date_to = await get_statistics_for_period(avito_account, period="week")
    operations = await get_active_operations_for_period(avito_account, period="week")
    items_with_metrics = await get_items_with_metrics(statistics=statistics, operations=operations, items=items)

    metrics["avito_account_name"] = avito_account.name
    metrics["telegram_id"] = avito_account.telegram_id
    metrics["total_metrics"] = await get_total_metrics(items_with_metrics=items_with_metrics,
                                                       items=items,
                                                       statistics=statistics)
    metrics["top"] = await get_top_5_items(items_with_metrics=items_with_metrics)
    metrics["chat_bot"] = await get_chat_bot_statistics(avito_account, date_from, date_to)
    metrics["period"] = {
        "date_from": date_from,
        "date_to": date_to
    }
    return metrics
