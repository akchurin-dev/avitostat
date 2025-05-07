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


def get_open_lead_by_contact(domain: str, contact_id: int, *, tlogger: TraceLogger) -> amo_api.Lead | None:
    contact = amo_api.get_contact(domain, contact_id, with_leads=True, tlogger=tlogger)

    if contact.lead_ids is None:
        return None

    tlogger.info(f"Contact id={contact_id} linked with leads: {contact.lead_ids}")

    for lead_id in contact.lead_ids:
        lead = amo_api.get_lead(domain, lead_id, tlogger=tlogger)

        if amo_pipelines.status_opened(lead.status_id):
            tlogger.info(f"Found opened lead id={lead_id}")
            return lead

    tlogger.info("All contact's leads are closed")
    return None


def define_lead(account: amo.models.AmoAccount, contact_id: int, advised_lead_id: int | None, *, tlogger: TraceLogger) -> amo_api.Lead | None:
    lead = None

    if advised_lead_id:
        tlogger.info(f"Got advised lead {advised_lead_id}")
        lead = amo_api.get_lead(account.domain, advised_lead_id, tlogger=tlogger)

    if lead is None or not amo_pipelines.status_opened(lead.status_id):
        tlogger.info(f"Lead wasn't advised or advised lead is closed")
        lead = get_open_lead_by_contact(account.domain, contact_id, tlogger=tlogger)

    # if lead is None:
    #     lead_id = amo_api.create_lead(account, contact_id, tlogger=tlogger)
    #     lead = amo_api.get_lead(account.domain, lead_id, tlogger=tlogger)
    #     tlogger.info(f"Didn't find opened leads. New lead (id={lead_id}) was created")

    return lead
