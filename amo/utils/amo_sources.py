import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def scan_new_origins(account_id: int, *, tlogger: TraceLogger) -> None:
    sources = amo_api.get_sources(account_id, tlogger=tlogger)

    for source in sources:
        amo.models.AmoOrigin.objects.get_or_create(
            amo_id=source.id,
            code=source.origin,
        )
