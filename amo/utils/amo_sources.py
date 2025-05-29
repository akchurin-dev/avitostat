import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def scan_new_origins(account_id: int, *, tlogger: TraceLogger) -> None:
    sources = amo_api.get_sources(account_id, tlogger=tlogger)

    existing_origins_ids: set[str] = set(
        amo.models.AmoOrigin.objects
        .filter(amo_id__in=[origin.id for origin in sources])
        .values_list("amo_id", flat=True)
    )

    tlogger.info({"existing_origins_ids": existing_origins_ids})

    nonexisting_origins: list[amo.models.AmoOrigin] = []

    for origin in sources:
        if str(origin.id) not in existing_origins_ids:
            nonexisting_origins.append(amo.models.AmoOrigin(
                amo_id=origin.id,
                account_id=account_id,
                name=origin.name,
                origin_title=origin.origin_title,
                source_name=origin.source_name,
                origin=origin.origin,
            ))

    tlogger.info({"origins ids for create": [origin.amo_id for origin in nonexisting_origins]})

    if nonexisting_origins:
        amo.models.AmoOrigin.objects.bulk_create(nonexisting_origins)

    origins_for_update: list[amo.models.AmoOrigin] = []

    for origin in sources:
        if str(origin.id) in existing_origins_ids:
            origins_for_update.append(amo.models.AmoOrigin(
                amo_id=origin.id,
                name=origin.name,
                origin_title=origin.origin_title,
                source_name=origin.source_name,
                origin=origin.origin,
            ))

    tlogger.info({"origins ids for update": [origin.amo_id for origin in origins_for_update]})

    if origins_for_update:
        amo.models.AmoOrigin.objects.bulk_update(origins_for_update, ["name", "origin_title", "source_name", "origin"])
