import time
from typing import NamedTuple

import amo.models
from amo.utils import amo_api
from amo.utils import amo_pipelines
from utils.logging import TraceLogger


class LeadContactPair(NamedTuple):
    lead: amo_api.Lead
    contact: amo_api.Contact


def change_lead_status(account: amo.models.AmoAccount, lead_id: int | str, status_id: int | str, *, tlogger: TraceLogger) -> None:
    data = {"status_id": int(status_id)}

    response = amo_api.openapi_request_by_account(
        account=account,
        method="PATCH",
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

    contact = amo_api.get_contact(account, contact_id, with_leads=True, tlogger=tlogger)

    if contact is None:
        raise Exception("Contact is None")

    if contact.lead_ids is None:
        return []

    tlogger.info(f"Contact id={contact_id} linked with leads: {contact.lead_ids}")

    open_leads: list[amo_api.Lead] = []

    for lead_id in contact.lead_ids:
        lead = amo_api.get_lead(account, lead_id, tlogger=tlogger)

        if lead.status_id is None:
            continue

        if amo_pipelines.status_opened(lead.status_id):
            open_leads.append(lead)

    if advised_lead_id:
        advised_lead = amo_api.get_lead(account, advised_lead_id, tlogger=tlogger)

        if advised_lead.status_id is not None and amo_pipelines.status_opened(advised_lead.status_id):
            open_leads.append(advised_lead)

    tlogger.info(f"Open leads: {[lead.id for lead in open_leads]}")

    return open_leads


def get_lead_contact_pair(account: amo.models.AmoAccount, lead_id: int | str, *, tlogger: TraceLogger) -> LeadContactPair:
    lead = amo_api.get_lead(
        account=account,
        lead_id=lead_id,
        with_contacts=True,
        tlogger=tlogger,
    )

    assert lead.contacts_ids is not None

    contact = amo_api.get_contact(
        account=account,
        contact_id=lead.contacts_ids[0],
        with_leads=False,
        tlogger=tlogger,
    )
    assert contact

    return LeadContactPair(lead, contact)


def get_lead_contact(account: amo.models.AmoAccount, lead: amo_api.Lead, *, tlogger: TraceLogger) -> amo_api.Contact | None:
    for also_retries in range(1, -1, -1):
        assert lead.contacts_ids is not None
        contact = amo_api.get_contact(
            account=account,
            contact_id=lead.contacts_ids[0],
            with_leads=False,
            tlogger=tlogger,
        )

        if contact:
            return contact

        if also_retries != 0:
            time.sleep(3)
            lead = amo_api.get_lead(account, lead.id, tlogger=tlogger)
    else:
        tlogger.error({"contact is empty": {
            "lead_contacts_ids": lead.contacts_ids,
        }})
        return None
