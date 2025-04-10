from amo.utils import amo_api
from utils.logging import TraceLogger


def find_text_field(name: str, fields: list[amo_api.Field]) -> amo_api.Field | None:
    for field in fields:
        if field.name == name and field.type == "text":
            return field

    return None


def get_or_create_field(domain: str, entity: amo_api.EntityEnum, name: str, *, tlogger: TraceLogger) -> amo_api.Field:
    fields = amo_api.get_fields(domain, entity, tlogger=tlogger)
    field = find_text_field(name, fields)

    if field:
        return field

    return amo_api.create_text_field(domain, entity, name, tlogger=tlogger)
