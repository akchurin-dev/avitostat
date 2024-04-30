from avito_account.api.api import get_items_list, get_statistics
from avito_account.api.get_operations import get_operations_for_range
from avito_account.models import AvitoAccount, Item
from conversion.models import ServiceType, Operation, Statistic


def items_to_db(avito_account: AvitoAccount):
    items = get_items_list(avito_account)
    items_to_create = []
    for item in items:
        items_to_create.append(Item(
            avito_account_id=avito_account.id,
            id=item.get("id"),
            address=item.get("address"),
            category=item.get("category"),
            status=item.get("status"),
            title=item.get("title"),
            price=item.get("price", None),
            url=item.get("url"),
        ))
    Item.objects.bulk_create(items_to_create)


def operations_to_db():
    # TODO bulc_create сделать если это возможно
    # TODO но надо учесть момент если уже существует ч

    start_date = "2024-01-01T00:00:00"
    end_date = "2024-01-31T23:59:59"
    avito_account: AvitoAccount = AvitoAccount.objects.filter(id=359794245).last()

    operations = get_operations_for_range(avito_account.access_token, start_date, end_date)
    if len(operations) > 0:
        for operation in operations:
            service_type, create = ServiceType.objects.get_or_create(
                service_name=operation.get("serviceName"),
                service_type=operation.get("serviceType"),
                service_id=operation.get("serviceId"),
            )

            Operation.objects.get_or_create(
                amount_bonus=operation.get("amountBonus"),
                amount_rub=operation.get("amountRub"),
                amount_total=operation.get("amountTotal"),
                item_id=operation.get("itemId"),
                name=operation.get("operationName"),
                type=operation.get("operationType"),
                service_id=service_type.id,
                updated_at=operation.get("updatedAt"),
            )


def statistic_to_db(avito_account: AvitoAccount):
    # TODO Проверить изначальный респонс посчитать не теряются ли статистики
    statistics = get_statistics(avito_account)
    if statistics:
        for statistic in statistics:
            item_id = statistic.get("itemId", )
            for date in statistic.get("stats"):
                Statistic.objects.get_or_create(
                    item_id=item_id,
                    date=date.get("date"),
                    uniq_contacts=date.get("uniqContacts"),
                    uniq_favorites=date.get("uniqFavorites"),
                    uniq_views=date.get("uniqViews"),
                )

