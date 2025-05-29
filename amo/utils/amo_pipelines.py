import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def get_status_by_name(
    account: amo.models.AmoAccount,
    pipeline_id: int,
    status_name: str,
    *,
    tlogger: TraceLogger,
) -> amo_api.PipelineStatus:

    statuses = amo_api.get_pipeline_statuses(account, pipeline_id, tlogger=tlogger)

    for status in statuses:
        if status.name == status_name:
            return status

    raise Exception(f"Status '{status_name}' from pipeline (id={pipeline_id}) is not found")


def syncronize_pipelines(account: amo.models.AmoAccount, *, tlogger: TraceLogger) -> None:
    statuses = amo_api.get_pipelines_statuses(account, tlogger=tlogger)

    existing_statuses_ids: set[int] = set(
        amo.models.AmoPipelineStatus.objects.filter(
            account=account,
            amo_id__in=[status.id for status in statuses],
        ).values_list("amo_id", flat=True)
    )

    statuses_for_create: list[amo.models.AmoPipelineStatus] = []
    statuses_for_update: list[amo.models.AmoPipelineStatus] = []

    for status in statuses:
        list_add_to = statuses_for_create

        if status.id in existing_statuses_ids:
            list_add_to = statuses_for_update

        list_add_to.append(amo.models.AmoPipelineStatus(
            account=account,
            pipeline_id=status.pipeline_id,
            pipeline_name=status.pipeline_name,
            amo_id=status.id,
            name=status.name,
        ))

    if statuses_for_create:
        amo.models.AmoPipelineStatus.objects.bulk_create(statuses_for_create)

    if statuses_for_update:
        amo.models.AmoPipelineStatus.objects.bulk_update(statuses_for_update, ["pipeline_name", "name"])

    statuses_for_delete = (
        amo.models.AmoPipelineStatus.objects
        .filter(account=account)
        .exclude(amo_id__in=[status.id for status in statuses])
    )

    statuses_for_delete.delete()


def status_opened(id: int) -> bool:
    return id not in [142, 143]  # Статусы "Релизовано" (id = 142) и "Закрыто и не реализовано" (id = 143)
