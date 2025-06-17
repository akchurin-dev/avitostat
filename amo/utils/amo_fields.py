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


def update_entity_fields(
    account: amo.models.AmoAccount,
    entity: amo_api.EntityEnum,
    instance_id: int | str,
    fields_values: dict[str, str | None],
    skip_null: bool = True,
    *,
    tlogger: TraceLogger,
) -> None:

    fields = amo_api.get_fields(account, entity, tlogger=tlogger)

    custom_fields_values = []

    for field_name, value in fields_values.items():
        if skip_null and value is None:
            continue

        field = find_text_field(field_name, fields, tlogger=tlogger)

        if field is None:
            field = amo_api.create_text_field(account, entity, field_name, tlogger=tlogger)

        custom_fields_values.append({
            "field_id": field.id,
            "values": [{"value": value}]
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
