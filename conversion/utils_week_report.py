from datetime import datetime
import datetime
import math

from avito_account.api.get_operations import get_active_operations_for_period
from avito_account.models import AvitoAccount
from conversion.api import get_statistics_for_period


def get_week_number():
    today = datetime.datetime.now()
    week_number = (today.day - 1) // 7
    return week_number


def get_costs_merged(operations) -> dict:
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


def get_conversions_for_week(statistics, operations: list) -> dict:
    conversions = {}
    week_number = get_week_number()
    costs_merged = get_costs_merged(operations=operations)
    if statistics:
        for statistic in statistics:
            itemId = statistic.get("itemId", None)
            if itemId:
                conversion_item = conversions.get(itemId, None)
                if conversion_item is None:
                    conversions[itemId] = {
                        'uniqContacts': statistic.get("stats")[week_number].get("uniqContacts"),
                        'uniqFavorites': statistic.get("stats")[week_number].get("uniqFavorites"),
                        'uniqViews': statistic.get("stats")[week_number].get("uniqViews"),
                    }

                    coast = costs_merged.get(itemId)

                    if coast:
                        uniq_contacts = statistic.get("stats")[week_number].get("uniqContacts")
                        uniq_favorites = statistic.get("stats")[week_number].get("uniqFavorites")
                        uniq_views = statistic.get("stats")[week_number].get("uniqViews")

                        if uniq_contacts != 0:
                            conversions[itemId]["amount_per_contact"] = math.floor(coast / uniq_contacts)
                        if uniq_favorites != 0:
                            conversions[itemId]["amount_per_favorite"] = math.floor(coast / uniq_favorites)
                        if uniq_views != 0:
                            conversions[itemId]["amount_per_view"] = math.floor(coast / uniq_views)
    return conversions


def get_week_report():
    avito_account = AvitoAccount.objects.filter(id=203199629).last()
    statistics = get_statistics_for_period(avito_account, period="week")  # Здесь токен рефрешится если он просрочен
    operations = get_active_operations_for_period(avito_account, period="week")
    conversions = get_conversions_for_week(statistics=statistics, operations=operations)
    return conversions
