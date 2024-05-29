from avito_account.api.get_operations import get_active_operations_for_period
from avito_account.models import AvitoAccount
from conversion.api import get_statistics_for_period
import math


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
    week_number = -1
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
                    if stats and len(stats) > week_number and stats[week_number] is not None:
                        metrics[itemId] = {
                            'itemTitle': item.get("title"),
                            'uniqContacts': statistic.get("stats")[week_number].get("uniqContacts"),
                            'uniqFavorites': statistic.get("stats")[week_number].get("uniqFavorites"),
                            'uniqViews': statistic.get("stats")[week_number].get("uniqViews"),
                        }

                    coast = costs_merged.get(itemId)

                    if coast:
                        stats = statistic.get("stats")
                        if stats and len(stats) > week_number and stats[week_number] is not None:
                            uniq_contacts = statistic.get("stats")[week_number].get("uniqContacts")
                            uniq_favorites = statistic.get("stats")[week_number].get("uniqFavorites")
                            uniq_views = statistic.get("stats")[week_number].get("uniqViews")

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
            "all": 0,
            "active": 0,
        },
        "total_contacts_count": 0,
        "total_views_count": 0,
        "total_favorites_count": 0,
        "total_coast": 0,
        "total_coast_per_contact": 0,

    }
    if items:
        total_metrics["total_items_count"] = {
            "all": len(items),
            "active": len(statistics)
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


async def get_week_report(avito_account: AvitoAccount):
    metrics = {}
    statistics, items = await get_statistics_for_period(avito_account, period="week")
    operations = await get_active_operations_for_period(avito_account, period="week")
    items_with_metrics = await get_items_with_metrics(statistics=statistics, operations=operations, items=items)

    metrics["avito_account_name"] = avito_account.name
    metrics["telegram_id"] = avito_account.telegram_id
    metrics["total_metrics"] = await get_total_metrics(items_with_metrics=items_with_metrics,
                                                       items=items,
                                                       statistics=statistics)
    metrics["top"] = await get_top_5_items(items_with_metrics=items_with_metrics)
    return metrics
