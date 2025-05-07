from slugify import slugify

from avito_account.models.models import AvitoAccount
import chat_bot.models
import messaging.api


def define_company_branch(avito_account: AvitoAccount, chat_id: str) -> chat_bot.models.CompanyBranch | None:
    chat = messaging.api.MessagingAPISync.get_chat_by_id(avito_account, chat_id)
    location: str | None = chat["context"]["value"].get("location", {}).get("title")

    if location is None:
        return None

    location_code = get_location_code(location)

    return chat_bot.models.CompanyBranch.objects.filter(account=avito_account, location_slug=location_code).first()


def get_location_code(location: str) -> str:
    return slugify(location, separator="_").upper()
