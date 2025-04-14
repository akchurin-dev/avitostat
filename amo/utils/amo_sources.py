import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def scan_new_origins(account_id: int, *, tlogger: TraceLogger) -> None:
    sources = amo_api.get_sources(account_id, tlogger=tlogger)
    origins = {(source.origin_id, source.origin) for source in sources}

    for origin in origins:
        amo.models.AmoOrigin.objects.get_or_create(
            amo_id=origin[0],
            code=origin[1],
        )
