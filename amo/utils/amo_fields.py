from typing import NamedTuple

import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


ENUM_TYPES = {
    "multiselect",
    "select",
}

TEXT_TYPES = {
    "multitext",
    "streetaddress",
    "text",
    "textarea",
    "url",
}

ENUM_EMPTY_VALUES = {
    None,
    "__null__",
    "__None__",
    "другой",
}


def update_entity_fields(
    account: amo.models.AmoAccount,
    entity: amo_api.EntityEnum,
    instance_id: int | str,
    fields_values: dict[str, str | list[str] | None],
    *,
    tlogger: TraceLogger,
) -> None:

    fields = amo_api.get_fields(account, entity, tlogger=tlogger)

    custom_fields_values = []

    for field_name, value in fields_values.items():
        if value is None:
            continue

        field = find_text_field(field_name, fields, tlogger=tlogger)

        if field and field.type in ENUM_TYPES:
            if isinstance(value, str) and value in ENUM_EMPTY_VALUES:
                continue

            if isinstance(value, list):
                value = [v for v in value if v not in ENUM_EMPTY_VALUES]
                if len(value) == 0:
                    continue

        if field is None:
            field = amo_api.create_text_field(account, entity, field_name, tlogger=tlogger)

        if isinstance(value, str):
            custom_fields_values.append({
                "field_id": field.id,
                "values": [{"value": value}]
            })
        elif isinstance(value, list):
            custom_fields_values.append({
                "field_id": field.id,
                "values": [{"value": v} for v in value]
            })

    amo_api.openapi_request_by_account(
        account=account,
        method="PATCH",
        action=f"/api/v4/{entity.value}/{instance_id}",
        json={"custom_fields_values": custom_fields_values},
        tlogger=tlogger,
    )

    tlogger.info({
        "message": f"Update {entity.value} id='{instance_id}'",
        "data": custom_fields_values,
    })


def find_text_field(name: str, fields: list[amo_api.Field], *, tlogger: TraceLogger) -> amo_api.Field | None:
    for field in fields:
        if field.name != name:
            continue

        if field.type not in TEXT_TYPES and field.type not in ENUM_TYPES:
            tlogger.info(f"Field '{field.name}' has type '{field.type}', it isn't supportable")
            continue

        return field

    tlogger.info(f"Field '{name}' not found")

    return None


def get_or_create_field(
    account: amo.models.AmoAccount,
    entity: amo_api.EntityEnum,
    name: str,
    *,
    tlogger: TraceLogger,
) -> amo_api.Field:

    fields = amo_api.get_fields(account, entity, tlogger=tlogger)
    field = find_text_field(name, fields, tlogger=tlogger)

    if field:
        return field

    return amo_api.create_text_field(account, entity, name, tlogger=tlogger)


def get_filled_fields(instance: amo_api.CustomFieldsContainer) -> list[amo_api.CustomFieldValue]:
    fields: list[amo_api.CustomFieldValue] = []

    if instance.custom_fields_values is None:
        return []

    for field_value in instance.custom_fields_values:
        if len(field_value.values) != 0 and field_value.values[0].value:
            fields.append(field_value)

    return fields


def get_empty_fields(
    account: amo.models.AmoAccount,
    instance: amo_api.CustomFieldsContainer,
    *,
    tlogger: TraceLogger,
) -> list[amo_api.Field]:

    entity: amo_api.EntityEnum | None = None

    if isinstance(instance, amo_api.Lead):
        entity = amo_api.EntityEnum.LEADS

    if isinstance(instance, amo_api.Contact):
        entity = amo_api.EntityEnum.CONTACTS

    if entity is None:
        raise ValueError(f"Unsupportable type, got {type(instance)}")

    all_fields = amo_api.get_fields(account, entity, tlogger=tlogger)
    filled_fields_ids = {field_value.field_id for field_value in get_filled_fields(instance)}
    empty_fields = [field for field in all_fields if field.id not in filled_fields_ids]

    tlogger.info(f"Found {len(empty_fields)} unknown fields")

    return empty_fields


def field_filled(field_value: amo_api.CustomFieldValue) -> bool:
    if field_value.field_type in TEXT_TYPES:
        return any(value.value for value in field_value.values)

    if field_value.field_type in ENUM_TYPES:
        return any(value.value not in ENUM_EMPTY_VALUES for value in field_value.values)

    raise Exception("Unknown field type, got " + field_value.field_type)


def get_filled_fillable_fields(
    chatbot: amo.models.AmoChatBot,
    lead: amo_api.Lead,
    contact: amo_api.Contact,
) -> dict[str, list[str]]:

    fillable_fields = amo.models.FillableField.objects.filter(chatbot=chatbot)
    known_fields_values: dict[str, list[str]] = {}

    for fillable_field in fillable_fields:
        entity = "Сделка"
        fields_values = lead.custom_fields_values
        if fillable_field.entity == amo.models.AmoEntity.CONTACT:
            entity = "Контакт"
            fields_values = contact.custom_fields_values

        for field_values in fields_values or []:
            if field_values.field_name != fillable_field.name:
                continue

            known_fields_values[f"{entity}.{fillable_field.name}"] = [value.value for value in field_values.values]
            break

    return known_fields_values
