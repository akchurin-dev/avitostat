import re
from typing import Iterable
from typing import Literal
from typing import NamedTuple

from django.db.models import F
from django.db.models import Q
from openai.types.responses import EasyInputMessageParam
from openai.types.responses import ResponseInputParam
from openai.types.responses import ResponseInputItemParam
from openai.types.responses import ResponseTextConfigParam
# from pydantic import BaseModel

import amo.models
from amo.utils import amo_api
from amo.utils import amo_fields
# from amo.utils import amo_leads
from amo.utils.amo_messages import Message
from amo.utils.amo_messages import MessageTypeEnum
from amo.utils.amo_transcriptions import TranscriptionsForMessages
from chat_bot.ai_utils import use_gpt_flag
from prompts import prompts
from utils import httpx_helper
from utils.logging import TraceLogger
from utils.miscellaneous import datetime_now_msk
from utils.openai_helper import openai_request


PHRASE_AUTHOR_REGEX = re.compile(r"^\s*\w+:\s*")


class AIAnswer(NamedTuple):
    answer: str
    tokens_prompt: int
    tokens_completion: int


def generate_answer(
    account: amo.models.AmoAccount,
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    known_info: dict[str, list[str]],
    # lead_id: int,
    *,
    tlogger: TraceLogger,
) -> AIAnswer:

    if not use_gpt_flag():
        return AIAnswer(answer="mock answer", tokens_prompt=0, tokens_completion=0)

    # lead, contact = amo_leads.get_lead_contact_pair(chatbot.account, lead_id, tlogger=tlogger)
    # all_fillable_fields = amo.models.FillableField.objects.filter(chatbot=chatbot, isolated_check=False)
    # unknown_fillable_fields = get_unknown_fillable_fields(account, all_fillable_fields, lead, contact, tlogger=tlogger)
    # available_pipeline_statuses = amo_api.get_pipeline_statuses(account, lead.pipeline_id, tlogger=tlogger)

    # gpt_messages = _get_gpt_messages(
    #     account=account,
    #     chatbot=chatbot,
    #     messages=messages,
    #     all_fillable_fields=all_fillable_fields,
    #     unknown_fillable_fields=unknown_fillable_fields,
    #     available_pipeline_statuses=available_pipeline_statuses,
    #     lead=lead,
    #     contact=contact,
    #     tlogger=tlogger,
    # )

    # text_format = get_text_format(
    #     chatbot=chatbot,
    #     fields=unknown_fillable_fields,
    #     field_for_answer=True,
    #     available_pipeline_statuses=available_pipeline_statuses,
    #     tlogger=tlogger,
    # )

    response = openai_request(
        input=_get_ai_input(account, chatbot, messages, known_info, tlogger=tlogger),
        tag=f"Amo | {account.domain} | generate answer",
        tlogger=tlogger,
    )

    tokens_prompt = tokens_completion = 0
    if response.usage:
        tokens_prompt = response.usage.input_tokens
        tokens_completion = response.usage.output_tokens

    return AIAnswer(
        answer=_delete_phrase_author_if_exists(response.output_text, tlogger=tlogger),
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
    )


# def _get_gpt_messages(
#     account: amo.models.AmoAccount,
#     chatbot: amo.models.AmoChatBot,
#     messages: list[ResponseInputItemParam],
#     all_fillable_fields: Iterable[amo.models.FillableField],
#     unknown_fillable_fields: Iterable[amo.models.FillableField],
#     available_pipeline_statuses: list[amo_api.PipelineStatus],
#     lead: amo_api.Lead,
#     contact: amo_api.Contact,
#     *,
#     tlogger: TraceLogger,
# ) -> ResponseInputParam:

#     current_status = None

#     for status in available_pipeline_statuses:
#         if status.id == lead.status_id:
#             current_status = status
#             break

#     if current_status is None:
#         raise Exception(f"Status (id={lead.status_id}) not found in pipeline (id={lead.pipeline_id})")

#     prompt = _get_prompt(account, chatbot, messages, unknown_fillable_fields, available_pipeline_statuses, current_status, tlogger=tlogger)

#     gpt_messages: ResponseInputParam = [{"role": "system", "content": prompt}]

#     if chatbot.duplicate_instructions:
#         gpt_messages.append({"role": "user", "content": chatbot.duplicate_instructions})

#     lead_contact_info = known_lead_contact_info(all_fillable_fields, lead, contact)
#     if lead_contact_info:
#         gpt_messages.append({"role": "user", "content": lead_contact_info})

#     gpt_messages.extend(messages)

#     return gpt_messages


def _get_ai_input(
    account: amo.models.AmoAccount,
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    known_info: dict[str, list[str]] | None = None,
    *,
    tlogger: TraceLogger,
) -> ResponseInputParam:

    base_prompt = (
        "Ты — менеджер, общающийся с клиентами. "
        "На основе переписки напиши ответ от имени менеджера. "
        "Не добавляй комментарии, пояснения или автора реплики — только текст ответа. "
        "Поле с ответом НЕ должно быть пустым. "
    )

    user_prompt = "Переписка с клиентом:\n" + _get_dialog_str(messages)
    if known_info:
        user_prompt = "\n".join(
            ["Что известно о клиенте и сделке, не переспрашивай о заполненных полях и не дублируй эти значения в ответном сообщении."]
            + [key + ": " + "; ".join(values) for key, values in known_info.items()]
        ) + "\n\n" + user_prompt

    ai_input: ResponseInputParam = [
        {
            "role": "system",
            "content": base_prompt + "\n\n\n" + _get_prompt(account, chatbot, messages, tlogger=tlogger),
        },
        *_get_images_ai_input(messages),
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

    return ai_input


# def known_lead_contact_info(
#     fillable_fields: Iterable[amo.models.FillableField],
#     lead: amo_api.Lead,
#     contact: amo_api.Contact,
# ) -> str | None:

#     known_lead_fields = amo_fields.get_filled_fields(lead)
#     known_contact_fields = amo_fields.get_filled_fields(contact)

#     fillable_fieds_names_descriptions = {field.name: field.description for field in fillable_fields}

#     known_lead_fields = [field for field in known_lead_fields if field.field_name in fillable_fieds_names_descriptions]
#     known_contact_fields = [field for field in known_contact_fields if field.field_name in fillable_fieds_names_descriptions]

#     if len(known_lead_fields) + len(known_contact_fields) == 0:
#         return None

#     paragraphs = ["О сделке и о контакте уже известна некоторая информация. Не спращивай о том, что уже извество."]

#     if known_lead_fields:
#         paragraphs.append(_get_entity_info_str("Информация о сделке", known_lead_fields, fillable_fieds_names_descriptions))

#     if known_contact_fields:
#         paragraphs.append(_get_entity_info_str("Информация о контакте", known_contact_fields, fillable_fieds_names_descriptions))

#     return "\n\n".join(paragraphs)


def _get_entity_info_str(
    title: str,
    known_fields: list[amo_api.CustomFieldValue],
    fillable_fields_names_descriptions: dict[str, str],
) -> str:

    assert known_fields

    lines = [title]

    for field_value in known_fields:
        line = ["-", field_value.field_name]

        description = fillable_fields_names_descriptions.get(field_value.field_name)
        if description:
            line.append("(" + description + ")")

        line.extend(["=", str(field_value.values[0].value)])

        lines.append(" ".join(line))

    return "\n".join(lines)


def amo_message_to_gpt_format(message: Message, transcriptions: TranscriptionsForMessages) -> ResponseInputItemParam:
    role: Literal["assistant", "user"] = "assistant"
    if message.incoming:
        role = "user"

    msg_gpt: ResponseInputItemParam

    if message.type == MessageTypeEnum.TEXT:
        assert message.text
        msg_gpt = EasyInputMessageParam({
            "role": role,
            "content": message.text,
        })
    elif message.type == MessageTypeEnum.PICTURE:
        assert message.file_url
        msg_gpt = EasyInputMessageParam({
            "role": role,
            "content": [{
                "type": "input_image",
                "image_url": message.file_url,
                "detail": "low",
            }],
        })
    elif message.type == MessageTypeEnum.VOICE:
        msg_gpt = EasyInputMessageParam({
            "role": role,
            "content": transcriptions.get_transcription(message),
        })
    else:
        raise Exception(f"Unknown message type, got {message.type}")

    return msg_gpt


def get_fillable_entity_schema(
    account: amo.models.AmoAccount,
    fields: Iterable[amo.models.FillableField],
    entity: amo_api.EntityEnum,
    *,
    tlogger: TraceLogger,
) -> dict | None:

    fillable_field_amo_field_pairs = get_fillable_field_amo_field_pairs(account, fields, entity, tlogger=tlogger)

    if len(fillable_field_amo_field_pairs) == 0:
        return None

    properties = {
        fillable_field.name: get_field_schema(amo_field, fillable_field)
            for fillable_field, amo_field in fillable_field_amo_field_pairs
    }

    return {
        "type": ["object", "null"],
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


def get_fillable_field_amo_field_pairs(
    account: amo.models.AmoAccount,
    fillable_fields: Iterable[amo.models.FillableField],
    entity: amo_api.EntityEnum,
    *,
    tlogger: TraceLogger,
) -> list[tuple[amo.models.FillableField, amo.models.AmoField | None]]:

    # all_amo_fields = amo_api.get_fields(account, entity, tlogger=tlogger)
    all_amo_fields = amo.models.AmoField.get_fields_by_account(account.amo_id, entity.db_value)
    fillable_field_amo_field_pairs: list[tuple[amo.models.FillableField, amo.models.AmoField | None]] = []

    for fillable_field in fillable_fields:
        if entity == amo_api.EntityEnum.LEADS and fillable_field.entity != amo.models.AmoEntity.LEAD:
            continue

        if entity == amo_api.EntityEnum.CONTACTS and fillable_field.entity != amo.models.AmoEntity.CONTACT:
            continue

        amo_field = amo_fields.find_text_field(fillable_field.name, all_amo_fields, tlogger=tlogger)
        fillable_field_amo_field_pairs.append((fillable_field, amo_field))

    return fillable_field_amo_field_pairs


def get_field_schema(amo_field: amo.models.AmoField | None, fillable_field: amo.models.FillableField) -> dict:
    schema = {
        "type": ["string", "null"],
        "description": fillable_field.description,
    }

    if amo_field and amo_field.type in amo_fields.ENUM_TYPES:
        enum_values = [
            field_enum.value
                for field_enum in amo_field.enums
                    if field_enum.value not in amo_fields.ENUM_EMPTY_VALUES
        ]

        # if len(enum_values) < 2:
        #     enum_values.extend(["__null__", "__None__"])
        enum_values.extend(["__null__", "__None__"])

        schema["enum"] = enum_values

    return schema


def _delete_phrase_author_if_exists(message: str, *, tlogger: TraceLogger) -> str:
    res = PHRASE_AUTHOR_REGEX.search(message)

    if res is None:
        tlogger.info(f"Prefix with phrase author isn't found in '{message}'")
        return message

    length = len(res.group(0))
    new_message = message[length:]

    tlogger.info(f"Found phrase author in '{message}', new variant is '{new_message}'")

    return new_message


# def get_unknown_fillable_fields(
#     account: amo.models.AmoAccount,
#     all_fillable_fields: Iterable[amo.models.FillableField],
#     lead: amo_api.Lead,
#     contact: amo_api.Contact,
#     *,
#     tlogger: TraceLogger,
# ) -> Iterable[amo.models.FillableField]:

#     empty_lead_fields = {f.name for f in amo_fields.get_empty_fields(account, lead, tlogger=tlogger)}
#     empty_contact_fields = {f.name for f in amo_fields.get_empty_fields(account, contact, tlogger=tlogger)}

#     lead_fillable_fields = [ff for ff in all_fillable_fields if ff.entity == amo.models.AmoEntity.LEAD]
#     contact_fillable_fields = [ff for ff in all_fillable_fields if ff.entity == amo.models.AmoEntity.CONTACT]

#     unknown_fillable_fields = [ff for ff in lead_fillable_fields if ff.name in empty_lead_fields]
#     unknown_fillable_fields.extend(ff for ff in contact_fillable_fields if ff.name in empty_contact_fields)

#     tlogger.info({"Unknown fillable fields": [ff.name for ff in unknown_fillable_fields]})

#     return unknown_fillable_fields


def _get_prompt(
    account: amo.models.AmoAccount,
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    # fields: Iterable[amo.models.FillableField],
    # available_pipeline_statuses: list[amo_api.PipelineStatus],
    # current_status: amo_api.PipelineStatus,
    *,
    tlogger: TraceLogger,
) -> str:

    prompt = ""
    prompt = _add_chatbot_prompt(prompt, account, chatbot, messages, tlogger=tlogger)
    # prompt = _add_fields_prompt(prompt, fields)

    # if not chatbot.change_status_only_when_qualification:
    #     prompt = _add_pipelines_prompt(
    #         prompt=prompt,
    #         pipeline_status_update_rules=chatbot.pipeline_status_update_rules,
    #         available_pipeline_statuses=available_pipeline_statuses,
    #         current_status=current_status,
    #     )

    return prompt


def _add_chatbot_prompt(
    prompt: str,
    account: amo.models.AmoAccount,
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    *,
    tlogger: TraceLogger,
) -> str:

    time_now = datetime_now_msk().time()
    prompts_qs = amo.models.AmoPrompt.objects.filter(
        Q(
            available_since=F("available_until"),
        ) | Q(
            available_since__lt=F("available_until"),
            available_since__lte=time_now,
            available_until__gte=time_now,
        ) | Q(
            Q(available_since__lte=time_now) | Q(available_until__gte=time_now),
            available_since__gt=F("available_until"),
        ),
        chatbot=chatbot,
    )

    chatbot_prompt = prompts.define_prompt(
        prompts_qs,
        _get_dialog_str(messages),
        module="Amo",
        account_name=account.domain,
        tlogger=tlogger,
    )

    if not chatbot_prompt:
        return prompt

    if prompt:
        prompt += "\n\n"

    return prompt + chatbot_prompt


def _get_images_ai_input(messages: list[ResponseInputItemParam]) -> list[ResponseInputItemParam]:
    images_ai_input: list[ResponseInputItemParam] = []
    images_count = 0

    for msg in messages:
        role = msg.get("role")
        if role is None:
            continue

        content = msg.get("content")
        if content is None or isinstance(content, str):
            continue

        images_urls = [image_url for content_item in content if (image_url := content_item.get("image_url"))]

        if len(images_urls) == 0:
            continue

        images_count += 1

        if httpx_helper.request("HEAD", images_urls[0]).is_success:
            images_ai_input.append(EasyInputMessageParam({
                "role": "user" if role == "user" else "assistant",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Изображение {images_count}",
                    },
                    {
                        "type": "input_image",
                        "image_url": images_urls[0],
                        "detail": "low",
                    },
                ],
            }))

    return images_ai_input


def _get_dialog_str(messages: list[ResponseInputItemParam]) -> str:
    replics: list[str] = []
    images_count = 0

    for msg in messages:
        role = msg.get("role")
        if not isinstance(role, str):
            continue

        author = {"assistant": "Менеджер", "user": "Клиент"}.get(role)
        if author is None:
            continue

        content = msg.get("content")
        if content is None:
            continue

        text: str

        if isinstance(content, str):
            text = content
        elif any(content_item.get("image_url") for content_item in content):
            images_count += 1
            text = f"<Изображение {images_count}>"
        else:
            text = "<Не текстовое сообщение>"

        replics.append(author + ": " + text)

    return "\n\n".join(replics)


# def _add_pipelines_prompt(
#     prompt: str,
#     pipeline_status_update_rules: str,
#     available_pipeline_statuses: list[amo_api.PipelineStatus],
#     current_status: amo_api.PipelineStatus,
# ) -> str:

#     if not pipeline_status_update_rules:
#         return prompt

#     new_articles = [
#         "Определи нужно ли перевести сделку в новый статус по следующим правилам:",
#         pipeline_status_update_rules,
#         "Доступные статусы: " + ", ".join([status.name for status in available_pipeline_statuses]),
#         f"Сейчас сделка находится в статусе '{current_status.name}'",
#     ]

#     new_text = "\n\n".join(new_articles)

#     if prompt:
#         prompt += "\n\n\n"

#     return prompt + new_text


# def _add_fields_prompt(prompt: str, fields: Iterable[amo.models.FillableField]) -> str:
#     if len(list(fields)) == 0:
#         return prompt

#     new_articles = ["Твоя задача узнать у клиента следующие данные"]

#     for field in fields:
#         new_articles.append("\n".join([
#             "Поле: " + field.name,
#             "Описание: " + field.description,
#         ]))

#     new_text = "\n\n".join(new_articles)

#     if prompt:
#         prompt += "\n\n\n"

#     return prompt + new_text
