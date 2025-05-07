import amo.models
from amo.utils import amo_api
from amo.utils import amo_pipelines
from utils.logging import TraceLogger


def change_lead_status(domain: str, lead_id: int | str, status_id: int | str, *, tlogger: TraceLogger) -> None:
    data = {"status_id": int(status_id)}

    response = amo_api._request_with_token(
        method="PATCH",
        domain=domain,
        action=f"/api/v4/{amo_api.EntityEnum.LEADS.value}/{lead_id}",
        json=data,
        tlogger=tlogger,
    )
    response.raise_for_status()

    tlogger.info(f"Lead (id={lead_id}) status was updated to status (id={status_id})")


def get_open_leads_by_contact(
    account: amo.models.AmoAccount,
    contact_id: int,
    advised_lead_id: int | None = None,
    *,
    tlogger: TraceLogger,
) -> list[amo_api.Lead]:

    contact = amo_api.get_contact(account.domain, contact_id, with_leads=True, tlogger=tlogger)

    if contact.lead_ids is None:
        return []

    tlogger.info(f"Contact id={contact_id} linked with leads: {contact.lead_ids}")

    open_leads: list[amo_api.Lead] = []

    for lead_id in contact.lead_ids:
        lead = amo_api.get_lead(account.domain, lead_id, tlogger=tlogger)

        if amo_pipelines.status_opened(lead.status_id):
            open_leads.append(lead)

    if advised_lead_id:
        advised_lead = amo_api.get_lead(account.domain, advised_lead_id, tlogger=tlogger)

        if amo_pipelines.status_opened(advised_lead.status_id):
            open_leads.append(advised_lead)

    tlogger.info(f"Open leads: {[lead.id for lead in open_leads]}")

    return open_leads
