import datetime

from loguru import logger

from django.conf import settings


EXPIRATION_TIME = datetime.timedelta(minutes=10)


_domain_to_user: dict[str, int] = {}
_domains_add_time: dict[str, datetime.datetime] = {}


def link_user_with_bitrix_domain(user_id: int, bitrix_domain: str):
    _delete_expired_links()
    _domain_to_user[bitrix_domain] = user_id
    _domains_add_time[bitrix_domain] = datetime.datetime.now(datetime.UTC)
    logger.info(f"User {user_id} linked with bitrix domain {bitrix_domain}")


def get_user_id(bitrix_domain: str) -> int | None:
    _delete_expired_links()
    user_id = _domain_to_user.pop(bitrix_domain, None)
    _domains_add_time.pop(bitrix_domain)
    return user_id


def get_installation_link(bitrix_domain: str) -> str:
    return f"https://{bitrix_domain}/market/detail/{settings.BITRIX_CLIENT_ID}/"


def _delete_expired_links():
    now = datetime.datetime.now(datetime.UTC)
    for domain in _domains_add_time.keys():
        if now - _domains_add_time[domain] > EXPIRATION_TIME:
            _domain_to_user.pop(domain)
            _domains_add_time.pop(domain)
