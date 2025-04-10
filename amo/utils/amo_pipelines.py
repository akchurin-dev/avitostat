import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def get_pipeline_status_by_lead(account_id: int, lead_id: int, *, tlogger: TraceLogger) -> amo.models.AmoPipelineStatus:
    account = amo.models.AmoAccount.objects.get(amo_id=account_id)
    lead = amo_api.get_lead(
        domain=account.domain,
        lead_id=lead_id,
        tlogger=tlogger,
    )

    pipeline_status = amo.models.AmoPipelineStatus.objects.get(
        account_id=account_id,
        pipeline_id=lead.pipeline_id,
        amo_id=lead.status_id,
    )

    tlogger.info(f"Lead (id={lead_id}) in status '{pipeline_status}'")

    return pipeline_status


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
