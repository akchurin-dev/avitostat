import amo.models
import amo_a5client.models
from amo.utils import amo_api
from amo.utils import amo_fields
from avito_account.models.models import AvitoAccount
from avito_account.models.models import AvitoItem
from utils.logging import TraceLogger


def fill_chatbot_task_with_avito_data(task: amo.models.AmoChatBotTask, lead: amo_api.Lead, *, tlogger: TraceLogger) -> bool:
    """ Return True if success """

    tlogger.info("Define avito account from lead fields")
    avito_account = get_avito_account(lead, tlogger=tlogger)

    tlogger.info("Define avito chat_id from lead fields")
    avito_chat_id = get_avito_chat_id(lead, tlogger=tlogger)

    if avito_account is not None and avito_chat_id is not None:
        task.avito_account = avito_account
        task.avito_chat_id = avito_chat_id
        task.save()

        return True

    tlogger.info("Avito info not found in lead fields, try match with avito messages")

    text_with_attachment = _include_attachment_to_text(task.text, task.message_type)
    message_contact_link = amo_a5client.models.MessageContactLink.get_by_amo_data(
        message_created_at_ts=int(task.message_created_at.timestamp()),
        text=text_with_attachment,
        author_name="",
        amo_account_id=task.account.pk,
    )

    if message_contact_link:
        assert message_contact_link.avito_account_id is not None
        assert message_contact_link.avito_chat_id is not None

        task.avito_account_id = message_contact_link.avito_account_id
        task.avito_chat_id = message_contact_link.avito_chat_id
        task.save()

        return True

    tlogger.info("Avito message not found")

    return False


def get_avito_account(lead: amo_api.Lead, *, tlogger: TraceLogger) -> AvitoAccount | None:
    assert lead.custom_fields_values is not None
    item_url_field_value = amo_fields.find_field_value(lead.custom_fields_values, "А5: ссылка")

    if item_url_field_value is None:
        tlogger.info("item url field not found in lead fields")
        return None

    url: str = item_url_field_value.values[0].value
    avito_item = AvitoItem.get_by_url(url)

    if avito_item is None:
        tlogger.info(f"avito item not found by url {url}")
        return None

    return avito_item.account


def get_avito_chat_id(lead: amo_api.Lead, *, tlogger: TraceLogger) -> str | None:
    assert lead.custom_fields_values is not None
    chat_url_field_value = amo_fields.find_field_value(lead.custom_fields_values, "А5: беседа avito")

    if chat_url_field_value is None:
        tlogger.info("chat url field not found in lead fields")
        return None

    # Example url https://www.avito.ru/profile/messenger/channel/u2i-_G5GIhIb5_djKOllhpG5UQ
    url: str = chat_url_field_value.values[0].value
    tlogger.info(f"Avito chat url: {url}")

    url_parts = url.split("/")

    if len(url_parts) < 7:
        tlogger.error("Incorrect avito chat url. Length less than 7 parts")
        return None

    chat_id = url_parts[6]

    if not chat_id.startswith("u2i-"):
        tlogger.error(f"Got strange chat id '{chat_id}'")
        return None

    return chat_id


def _include_attachment_to_text(text: str, attachment_type: str | None) -> str:
    if attachment_type is None:
        return text

    if attachment_type == amo.models.AmoChatBotTask.MessageType.TEXT:
        return text

    if text:
        text += "\n\n---------------------\n\n"

    text += "Attachment type: " + attachment_type
    return text
