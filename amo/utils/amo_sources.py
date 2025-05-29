import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def scan_new_origins(account_id: int, *, tlogger: TraceLogger) -> None:
    sources = amo_api.get_sources(account_id, tlogger=tlogger)

    existing_origins_ids = set(
        amo.models.AmoOrigin.objects
        .filter(amo_id__in=[origin.id for origin in sources])
        .values_list("amo_id", flat=True)
    )

    not_existing_origins: list[amo.models.AmoOrigin] = []

    for origin in sources:
        if origin.id not in existing_origins_ids:
            not_existing_origins.append(amo.models.AmoOrigin(
                amo_id=origin.id,
                account_id=account_id,
                name=origin.name,
                origin_title=origin.origin_title,
                source_name=origin.source_name,
                origin=origin.origin,
            ))

    if not_existing_origins:
        amo.models.AmoOrigin.objects.bulk_create(not_existing_origins)

    origins_for_update: list[amo.models.AmoOrigin] = []

    for origin in sources:
        if origin.id in existing_origins_ids:
            origins_for_update.append(amo.models.AmoOrigin(
                amo_id=origin.id,
                name=origin.name,
                origin_title=origin.origin_title,
                source_name=origin.source_name,
                origin=origin.origin,
            ))

    if origins_for_update:
        amo.models.AmoOrigin.objects.bulk_update(origins_for_update, ["name", "origin_title", "source_name", "origin"])
