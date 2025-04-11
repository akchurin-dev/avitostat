from amo.utils import amo_api
from amo.utils import amo_fields
from utils.logging import TraceLogger


def update_entity_fields(
    domain: str,
    entity: amo_api.EntityEnum,
    instance_id: int | str,
    fields_values: dict[str, str | None],
    skip_null: bool = True,
    *,
    tlogger: TraceLogger,
) -> None:

    fields = amo_api.get_fields(domain, entity, tlogger=tlogger)

    custom_fields_values = []

    for field_name, value in fields_values.items():
        if skip_null and value is None:
            continue

        field = amo_fields.find_text_field(field_name, fields)

        if field is None:
            field = amo_api.create_text_field(
                domain=domain,
                entity=entity,
                name=field_name,
                tlogger=tlogger,
            )

        custom_fields_values.append({
            "field_id": field.id,
            "values": [{"value": value}]
        })

    amo_api._request_with_token(
        method="PATCH",
        domain=domain,
        action=f"/api/v4/{entity.value}/{instance_id}",
        json={"custom_fields_values": custom_fields_values},
        tlogger=tlogger,
    )
