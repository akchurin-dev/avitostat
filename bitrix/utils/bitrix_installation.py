from loguru import logger

from django.conf import settings


_domain_to_user = dict()


def link_user_with_bitrix_domain(user_id: int, bitrix_domain: str):
    _domain_to_user[bitrix_domain] = user_id
    logger.info(f"User {user_id} linked with bitrix domain {bitrix_domain}")


def get_user_id(bitrix_domain: str) -> int | None:
    user_id = _domain_to_user.pop(bitrix_domain, None)
    return user_id


def get_installation_link(bitrix_domain: str) -> str:
    return f"https://{bitrix_domain}/market/detail/{settings.BITRIX_CLIENT_ID}/"
