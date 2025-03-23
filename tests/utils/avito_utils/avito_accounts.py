import httpx
from pydantic import BaseModel

from tests import config as global_config
from tests.config import avito_config
from tests.utils import avitostat_test_api
from tests.utils.avito_utils import avito_api


class AvitoAccount(BaseModel):
    id: int
    name: str


def get_avito_account_info(access_token: str, refresh_token: str) -> AvitoAccount:
    """ https://developers.avito.ru/api-catalog/user/documentation#operation/getUserInfoSelf """

    action = "/core/v1/accounts/self"

    headers = {
        "Authorization": "Bearer " + access_token,
    }

    response = avito_api.avito_client.get(action, headers=headers)
    response.raise_for_status()

    return AvitoAccount.model_validate(response.json())


def init_config_seller_data():
    if global_config.SELLER_AVITO_ACCOUNT_ID:
        avito_account = avitostat_test_api.get_avito_account(avito_config.config.seller_avito_account_id)
        avito_config.config.seller_access_token = avito_account.access_token
        avito_config.config.seller_refresh_token = avito_account.refresh_token
        return

    avito_account = get_avito_account_info(
        access_token=avito_config.config.seller_access_token,
        refresh_token=avito_config.config.seller_refresh_token,
    )
    global_config.SELLER_AVITO_ACCOUNT_ID = avito_account.id


def get_or_create_avito_account(created_by_user_id: int) -> tuple[avitostat_test_api.AvitoAccount, bool]:
    if global_config.SELLER_AVITO_ACCOUNT_ID:
        avito_account = avitostat_test_api.get_avito_account(global_config.SELLER_AVITO_ACCOUNT_ID)
        global_config.SUMMARY_CHAT_ID = avito_account.telegram_id
        return avito_account, False

    return create_or_update_avito_account(created_by_user_id)


def create_or_update_avito_account(created_by_user_id: int) -> tuple[avitostat_test_api.AvitoAccount, bool]:
    avito_account, created = avitostat_test_api.create_or_update_avito_account(
        access_token=avito_config.config.seller_access_token,
        refresh_token=avito_config.config.seller_refresh_token,
        telegram_id=str(avito_config.config.summary_chat_id),
        created_by_id=created_by_user_id,
    )
    global_config.SUMMARY_CHAT_ID = avito_account.telegram_id
    return avito_account, created
