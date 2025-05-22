from amo.utils import amo_api
from utils.logging import TraceLogger


ENUM_TYPES = {
    "multiselect",
    "select",
}

TEXT_TYPES = {
    "streetaddress",
    "text",
    "textarea",
    "url",
}


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


def get_or_create_field(domain: str, entity: amo_api.EntityEnum, name: str, *, tlogger: TraceLogger) -> amo_api.Field:
    fields = amo_api.get_fields(domain, entity, tlogger=tlogger)
    field = find_text_field(name, fields, tlogger=tlogger)

    if field:
        return field

    return amo_api.create_text_field(domain, entity, name, tlogger=tlogger)
