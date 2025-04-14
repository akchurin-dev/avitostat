import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def get_status_by_name(domain: str, pipeline_id: int, status_name: str, *, tlogger: TraceLogger) -> amo_api.PipelineStatus:
    statuses = amo_api.get_pipeline_statuses(domain, pipeline_id, tlogger=tlogger)

    for status in statuses:
        if status.name == status_name:
            return status

    raise Exception(f"Status '{status_name}' from pipeline (id={pipeline_id}) is not found")


def syncronize_pipelines(domain: str, *, tlogger: TraceLogger) -> None:
    account = amo.models.AmoAccount.objects.get(domain=domain)
    statuses = amo_api.get_pipelines_statuses(domain, tlogger=tlogger)

    for status in statuses:
        amo.models.AmoPipelineStatus.objects.update_or_create(
            account=account,
            pipeline_id=status.pipeline_id,
            amo_id=status.id,
            defaults={
                "pipeline_name": status.pipeline_name,
                "name": status.name,
            },
        )

    non_existing = (
        amo.models.AmoPipelineStatus.objects
        .filter(account=account)
        .exclude(amo_id__in=[status.id for status in statuses])
    )
    non_existing.delete()
