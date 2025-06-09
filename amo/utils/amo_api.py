from __future__ import annotations

from enum import Enum
from typing import Any
from typing import NamedTuple

import pydantic
from pydantic import BaseModel

from amo import models as amo_models
from amo.utils import amo_tokens
from utils.logging import TraceLogger
from utils import httpx_helper


class EntityEnum(Enum):
    CONTACTS = "contacts"
    COMPANIES = "companies"
    LEADS = "leads"


class Account(BaseModel):
    id: int
    name: str
    amojo_id: str


def get_account_info(domain: str, access_token: str, *, tlogger: TraceLogger) -> Account:
    """ https://www.amocrm.ru/developers/content/crm_platform/account-info """

    url = "https://" + domain + "/api/v4/account"

    headers = {
        "Authorization": "Bearer " + access_token,
    }

    params = {
        "with": "amojo_id",
    }

    response = httpx_helper.request(
        method="GET",
        url=url,
        params=params,
        headers=headers,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return Account.model_validate_json(response.text)


def get_lead_events(account_id: str, lead_id: str, tlogger: TraceLogger) -> list[dict]:
    action = f"/ajax/v3/leads/{lead_id}/events_timeline"

    # params = {
    #     "filter[created_at][gte_lte]": "1743032621.2521",
    # }

    response = _request_with_csrf(
        method="GET",
        account_id=account_id,
        action=action,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return response.json()["_embedded"]["items"]


def send_message(account: amo_models.AmoAccount, chat_id: str, text: str, tlogger: TraceLogger) -> None:
    action = f"/v1/chats/{account.amojo_id}/{chat_id}/messages"

    data = {
        "text": text
    }

    response = _amojo_request(
        account=account,
        method="POST",
        action=action,
        json=data,
        tlogger=tlogger,
    )
    response.raise_for_status()


class CustomFieldValue(BaseModel):
    class Value(BaseModel):
        value: Any

        model_config = pydantic.ConfigDict(extra="allow")

    field_id: int
    field_name: str
    field_code: str | None
    field_type: str
    values: list[Value]


class Lead(BaseModel):
    id: int
    pipeline_id: int
    status_id: int | None = None
    custom_fields_values: list[CustomFieldValue] | None
    contacts_ids: list[int] | None = None


def get_lead(account: amo_models.AmoAccount, lead_id: int | str, *, tlogger: TraceLogger) -> Lead:
    action = f"/api/v4/leads/{lead_id}"

    params = {
        "with": ",".join(["contacts"]),
    }

    response = openapi_request_by_account(
        account=account,
        method="GET",
        action=action,
        params=params,
        tlogger=tlogger,
    )
    response.raise_for_status()

    data = response.json()
    data["contacts_ids"] = [c["id"] for c in data["_embedded"]["contacts"]]

    return Lead.model_validate(data)


def create_lead(account: amo_models.AmoAccount, contact_id: int, *, tlogger: TraceLogger) -> int:
    """ https://www.amocrm.ru/developers/content/crm_platform/leads-api#leads-add """

    action = "/api/v4/leads"

    data = [{
        "_embedded": {
            "contacts": [{
                "id": contact_id,
                "is_main": True,
            }],
        },
    }]

    response = openapi_request_by_account(
        account=account,
        method="POST",
        action=action,
        json=data,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return response.json()["_embedded"]["leads"][0]["id"]


def all_leads(domain: str, *, tlogger: TraceLogger):
    page = 0

    while True:
        leads_page = get_leads_page(domain, page, tlogger=tlogger)

        for lead in leads_page.leads:
            yield lead

        if leads_page.next_href is None:
            return

        page += 1


class LeadsPage(NamedTuple):
    leads: list[Lead]
    next_href: str | None


def get_leads_page(domain: str, page: int = 0, limit: int = 250, *, tlogger: TraceLogger) -> LeadsPage:
    """ https://www.amocrm.ru/developers/content/crm_platform/leads-api#leads-list """

    action = "/api/v4/leads"

    params = {
        "page": page,
        "limit": limit,
    }

    response = _request_with_token(
        method="GET",
        domain=domain,
        action=action,
        params=params,
        tlogger=tlogger,
    )
    response.raise_for_status()
    data= response.json()

    leads = [Lead.model_validate(lead) for lead in data["_embedded"]["leads"]]

    tlogger.info(f"Got {len(leads)} leads (page={page}, limit={limit})")

    next = data["_links"].get("next")
    next_href = None
    if next:
        next_href = next.get("href")

    return LeadsPage(leads, next_href)


class Contact(BaseModel):
    id: int
    name: str
    first_name: str | None = None
    last_name: str | None = None
    lead_ids: list[int] | None = None
    custom_fields_values: list[CustomFieldValue] | None


def get_contact(account: amo_models.AmoAccount, contact_id: int | str, with_leads: bool = False, *, tlogger: TraceLogger) -> Contact:
    """ https://www.amocrm.ru/developers/content/crm_platform/contacts-api#contact-detail """

    action = f"/api/v4/contacts/{contact_id}"

    params = None
    if with_leads:
        params = {
            "with": EntityEnum.LEADS.value
        }

    response = openapi_request_by_account(
        account=account,
        method="GET",
        action=action,
        params=params,
        tlogger=tlogger,
    )
    response.raise_for_status()

    contact_json = response.json()

    if with_leads:
        contact_json["lead_ids"] = [lead["id"] for lead in contact_json["_embedded"]["leads"]]

    return Contact.model_validate(contact_json)


class PipelineStatus(BaseModel):
    id: int
    name: str
    pipeline_id: int
    pipeline_name: str


def get_pipelines_statuses(account: amo_models.AmoAccount, *, tlogger: TraceLogger) -> list[PipelineStatus]:
    action = "/api/v4/leads/pipelines"

    response = openapi_request_by_account(
        account=account,
        method="GET",
        action=action,
        tlogger=tlogger,
    )
    response.raise_for_status()

    data = response.json()
    statuses: list[PipelineStatus] = []

    for pipeline in data["_embedded"]["pipelines"]:
        for status in pipeline["_embedded"]["statuses"]:
            statuses.append(PipelineStatus(
                id=status["id"],
                name=status["name"],
                pipeline_id=pipeline["id"],
                pipeline_name=pipeline["name"],
            ))

    return statuses


def get_pipeline_statuses(account: amo_models.AmoAccount, pipeline_id: int | str, *, tlogger: TraceLogger) -> list[PipelineStatus]:
    action = f"/api/v4/leads/pipelines/{pipeline_id}"

    response = openapi_request_by_account(account, "GET", action, tlogger=tlogger)
    response.raise_for_status()

    pipeline = response.json()
    statuses: list[PipelineStatus] = []

    for status in pipeline["_embedded"]["statuses"]:
        statuses.append(PipelineStatus(
            id=status["id"],
            name=status["name"],
            pipeline_id=pipeline["id"],
            pipeline_name=pipeline["name"],
        ))

    return statuses


class FieldEnum(BaseModel):
    id: int
    sort: int
    value: str


class Field(BaseModel):
    id: int
    name: str
    type: str
    code: str | None = None
    enums: list[FieldEnum] | None = None


def create_text_field(account: amo_models.AmoAccount, entity: EntityEnum, name: str, *, tlogger: TraceLogger) -> Field:
    """ https://www.amocrm.ru/developers/content/crm_platform/custom-fields#Создание-дополнительных-полей-сущности """

    action = f"/api/v4/{entity.value}/custom_fields"

    data = {
        "type": "text",
        "name": name,
    }

    response = openapi_request_by_account(
        account=account,
        method="POST",
        action=action,
        json=data,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return Field.model_validate(response.json())


def get_fields(account: amo_models.AmoAccount, entity: EntityEnum, *, tlogger: TraceLogger) -> list[Field]:
    """ https://www.amocrm.ru/developers/content/crm_platform/custom-fields#Список-полей-сущности """

    action = f"/api/v4/{entity.value}/custom_fields"

    response = openapi_request_by_account(
        account=account,
        method="GET",
        action=action,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return [Field.model_validate(f) for f in response.json()["_embedded"]["custom_fields"]]


class Source(BaseModel):
    id: int
    name: str
    origin_title: str
    source_name: str
    origin: str


def get_sources(account_id: int, *, tlogger: TraceLogger) -> list[Source]:
    action = "/ajax/v4/sources"

    response = _request_with_csrf("GET", account_id, action, tlogger=tlogger)
    response.raise_for_status()
    data = response.json()

    sources: list[Source] = []

    for s in data["_embedded"]["sources"]:
        try:
            source = Source.model_validate(s)

            if source.origin.strip():
                sources.append(source)
        except pydantic.ValidationError as e:
            tlogger.info({
                "title": "Invalid source",
                "error": e,
                "source": s,
            })

    return sources


def openapi_request_by_account(
    account: amo_models.AmoAccount,
    method: httpx_helper.MethodType,
    action: str,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | list | None = None,
    headers: dict | None = None,
    retry: bool = False,
    *,
    tlogger: TraceLogger,
):
    return _request_with_token(
        method=method,
        domain=account.domain,
        action=action,
        params=params,
        data=data,
        json=json,
        headers=headers,
        retry=retry,
        tlogger=tlogger,
    )


def _request_with_token(
    method: httpx_helper.MethodType,
    domain: str,
    action: str,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | list | None = None,
    headers: dict | None = None,
    retry: bool = False,
    *,
    tlogger: TraceLogger,
):
    account = amo_models.AmoAccount.objects.get(domain=domain)
    headers = httpx_helper.add_bearer(headers, account.access_token)

    response = httpx_helper.request(
        method=method,
        url="https://" + domain + action,
        params=params,
        data=data,
        json=json,
        headers=headers,
        tlogger=tlogger,
    )

    if not retry and response.status_code == 401:
        amo_tokens.update_tokens(
            domain=domain,
            refresh_token=account.refresh_token,
        )
        return _request_with_token(
            method=method,
            domain=domain,
            action=action,
            params=params,
            data=data,
            json=json,
            headers=headers,
            retry=True,
            tlogger=tlogger,
        )

    return response


def _request_with_csrf(
    method: httpx_helper.MethodType,
    account_id: str | int,
    action: str,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | None = None,
    headers: dict | None = None,
    retry: bool = False,
    *,
    tlogger: TraceLogger,
):
    account = amo_models.AmoAccount.objects.get(amo_id=account_id)

    url = "https://" + account.domain + action

    cookies_data = {
        "session_id": account.cookies_session_id or "",
        "csrf_token": account.cookies_csrf_token or "",
        "access_token": account.cookies_access_token or "",
        "refresh_token": account.cookies_refresh_token or "",
    }

    cookies_str = "; ".join([k + "=" + str(v) for k, v in cookies_data.items()])
    headers = httpx_helper.add_header(headers, key="Cookie", value=cookies_str)

    response = httpx_helper.request(
        method=method,
        url=url,
        params=params,
        data=data,
        json=json,
        headers=headers,
        tlogger=tlogger,
    )

    if not retry and response.status_code == 401:
        amo_tokens.update_hidden_api_tokens(account_id, tlogger=tlogger)
        return _request_with_csrf(
            method=method,
            account_id=account_id,
            action=action,
            params=params,
            data=data,
            json=json,
            headers=headers,
            retry=True,
            tlogger=tlogger,
        )

    return response


def _amojo_request(
    account: amo_models.AmoAccount,
    method: httpx_helper.MethodType,
    action: str,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | None = None,
    headers: dict | None = None,
    retry: bool = False,
    *,
    tlogger: TraceLogger,
):
    amojo_token = account.amojo_access_token
    headers = httpx_helper.add_header(headers, key="X-Auth-Token", value=amojo_token)

    response = httpx_helper.request(
        method=method,
        url="https://amojo.amocrm.ru" + action,
        params=params,
        data=data,
        json=json,
        headers=headers,
        tlogger=tlogger,
    )

    if not retry and response.status_code == 401:
        amo_tokens.update_hidden_api_tokens(account.amo_id, tlogger=tlogger)
        return _amojo_request(
            account=account,
            method=method,
            action=action,
            params=params,
            data=data,
            json=json,
            headers=headers,
            retry=True,
            tlogger=tlogger,
        )

    return response
