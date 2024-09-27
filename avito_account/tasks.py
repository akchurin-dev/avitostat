from avito_account.api.api import get_item_info
from base.celery import celery_app


@celery_app.task(name='messaging.tasks.e_item_get_title_task')
def excluded_item_get_title_task(new_excluded_item):
    item_info_json = get_item_info(
        access_token=new_excluded_item.avito_account.access_token,
        user_id=str(new_excluded_item.avito_account.id),
        item_id=str(new_excluded_item.id),
    )
    print(123)
