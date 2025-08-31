from django.db.models.query import QuerySet

from avito_account.models.models import AvitoAccount
from avito_account.models.models import AvitoItem
from chat_bot.utils import avito_api
from utils.logging import TraceLogger


def actualize_avito_account_items(account: AvitoAccount, *, tlogger: TraceLogger) -> None:
    items_in_avito = list(avito_api.get_items_list(account, tlogger=tlogger))

    AvitoItem.delete_non_existing(
        account_id=account.pk,
        existing_items_ids=[item.id for item in items_in_avito],
    )

    db_items = AvitoItem.get_by_account(account.pk)
    _update_items(db_items, items_in_avito)
    _create_items(account, db_items, items_in_avito)


def _update_items(db_items: QuerySet[AvitoItem], items_in_avito: list[avito_api.ItemInList]) -> None:
    ids_to_avito_items: dict[int, avito_api.ItemInList] = {item.id: item for item in items_in_avito}
    items_for_update: list[AvitoItem] = []

    for db_item in db_items:
        item_in_avito = ids_to_avito_items[db_item.id]
        changed = False

        if db_item.address != item_in_avito.address:
            db_item.address = item_in_avito.address
            changed = True

        if db_item.price != item_in_avito.price:
            db_item.price = item_in_avito.price
            changed = True

        if db_item.status != item_in_avito.status.value:
            db_item.status = item_in_avito.status.value
            changed = True

        if db_item.title != item_in_avito.title:
            db_item.title = item_in_avito.title
            changed = True

        if db_item.url != item_in_avito.url:
            db_item.url = item_in_avito.url
            changed = True

        if changed:
            items_for_update.append(db_item)

    AvitoItem.objects.bulk_update(
        objs=items_for_update,
        fields=[
            "address",
            "price",
            "status",
            "title",
            "url",
        ],
    )


def _create_items(
    account: AvitoAccount,
    db_items: QuerySet[AvitoItem],
    items_in_avito: list[avito_api.ItemInList],
) -> None:

    existing_ids: set[int] = {item.id for item in db_items}
    items_for_create: list[AvitoItem] = []

    for item_in_avito in items_in_avito:
        if item_in_avito.id in existing_ids:
            continue

        items_for_create.append(
            AvitoItem.create_instance(
                account_id=account.pk,
                id=item_in_avito.id,
                url=item_in_avito.url,
                title=item_in_avito.title,
                address=item_in_avito.address,
                price=item_in_avito.price,
                status=item_in_avito.status.value,
            )
        )

    AvitoItem.objects.bulk_create(items_for_create)
