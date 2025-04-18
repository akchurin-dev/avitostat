from amo.utils import amo_api
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

    assert contact.lead_ids is not None
    contact_leads = set(contact.lead_ids)

    for lead in amo_api.all_leads(domain, tlogger=tlogger):
        if lead.status_id in [142, 143]:  # Статусы "Релизовано" (id = 142) и "Закрыто и не реализовано" (id = 143)
            continue

        if lead.id in contact_leads:
            return lead

    return None
