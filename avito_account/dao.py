from avito_account.api.api import get_items_list
from avito_account.models import AvitoAccount, Item


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
