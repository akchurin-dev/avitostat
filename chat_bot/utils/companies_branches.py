from __future__ import annotations

from slugify import slugify

import chat_bot.models
import messaging.api
from avito_account.models.models import AvitoAccount
from utils.logging import TraceLogger


def define_company_branch(avito_account: AvitoAccount, chat_id: str, *, tlogger: TraceLogger) -> chat_bot.models.CompanyBranch | None:
    chat = messaging.api.get_chat_by_id(avito_account, chat_id, tlogger=tlogger)
    location: str | None = chat["context"]["value"].get("location", {}).get("title")

    if location is None:
        return None

    location_code = get_location_code(location)

    return chat_bot.models.CompanyBranch.objects.filter(account=avito_account, location_slug=location_code).first()


def get_location_code(location: str) -> str:
    return slugify(location, separator="_").upper()
