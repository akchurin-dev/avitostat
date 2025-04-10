from tests.config import avito_config
from tests.utils import avitostat_test_api


def update_tokens_in_test_conf():
    avito_account = avitostat_test_api.get_avito_account(avito_account_id=avito_config.config.seller_avito_account_id)
    if avito_account is None:
        return

    if avito_account.access_token:
        avito_config.config.seller_access_token = avito_account.access_token

    if avito_account.refresh_token:
        avito_config.config.seller_refresh_token = avito_account.refresh_token


def update_tokens_in_test_conf_decorator(func):
    def inner_func(*args, **kwargs):
        update_tokens_in_test_conf()
        res = func(*args, **kwargs)
        update_tokens_in_test_conf()
        return res

    return inner_func
