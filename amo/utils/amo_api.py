from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict

from amo import models as amo_models
from amo.utils import amo_tokens
from base import settings
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


def subscribe_to_new_messages(domain: str, tlogger: TraceLogger) -> None:
    """ https://www.amocrm.ru/developers/content/crm_platform/webhooks-api#webhook-subscribe """

    action = "/api/v4/webhooks"

    data = {
        "destination": "https://" + settings.AMO_WEBHOOK_DOMAIN + "/amo/webhook-inbox",
        "settings": ["add_message"],
    }

    response = _request_with_token("POST", domain, action, json=data, tlogger=tlogger)
    response.raise_for_status()


def unsubscribe_from_messages(domain: str, tlogger: TraceLogger) -> None:
    """ https://www.amocrm.ru/developers/content/crm_platform/webhooks-api#webhooks-delete """

    action = "/api/v4/webhooks"

    data = {
        "destination": "https://" + settings.AMO_WEBHOOK_DOMAIN + "/amo/oauth",
    }

    response = _request_with_token(
        method="DELETE",
        domain=domain,
        action=action,
        data=data,
        tlogger=tlogger,
    )
    response.raise_for_status()


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


def send_message(account_id: str, chat_id: str, text: str, tlogger: TraceLogger) -> None:
    account = amo_models.AmoAccount.objects.get(amo_id=account_id)
    action = f"/v1/chats/{account.amojo_id}/{chat_id}/messages"

    data = {
        "text": text
    }
    
    response = _amojo_request(
        method="POST",
        action=action,
        account=account,
        json=data,
        tlogger=tlogger,
    )
    response.raise_for_status()


class CustomFieldValue(BaseModel):
    class Value(BaseModel):
        value: Any

        model_config = ConfigDict(extra="allow")

    field_id: int
    field_name: str
    field_code: str | None
    field_type: str
    values: list[Value]


class Lead(BaseModel):
    id: int
    pipeline_id: int
    status_id: int
    custom_fields_values: list[CustomFieldValue] | None
    contacts_ids: list[int]


def get_lead(domain: str, lead_id: int | str, *, tlogger: TraceLogger) -> Lead:
    action = f"/api/v4/leads/{lead_id}"

    params = {
        "with": ",".join(["contacts"]),
    }

    response = _request_with_token(
        method="GET",
        domain=domain,
        action=action,
        params=params,
        tlogger=tlogger,
    )
    response.raise_for_status()

    data = response.json()
    data["contacts_ids"] = [c["id"] for c in data["_embedded"]["contacts"]]

    return Lead.model_validate(data)


class Contact(BaseModel):
    id: int
    name: str
    first_name: str
    last_name: str
    custom_fields_values: list[CustomFieldValue] | None


def get_contact(domain: str, contact_id: int | str, *, tlogger: TraceLogger) -> Contact:
    """ https://www.amocrm.ru/developers/content/crm_platform/contacts-api#contact-detail """

    action = f"/api/v4/contacts/{contact_id}"

    response = _request_with_token(
        method="GET",
        domain=domain,
        action=action,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return Contact.model_validate(response.json())


class PipelineStatus(BaseModel):
    id: int
    name: str
    pipeline_id: int
    pipeline_name: str


def get_pipelines_statuses(domain: str, *, tlogger: TraceLogger) -> list[PipelineStatus]:
    action = "/api/v4/leads/pipelines"

    response = _request_with_token(
        method="GET",
        domain=domain,
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


class Field(BaseModel):
    id: int
    name: str
    code: str | None
    type: str


def create_text_field(domain: str, entity: EntityEnum, name: str, *, tlogger: TraceLogger) -> Field:
    """ https://www.amocrm.ru/developers/content/crm_platform/custom-fields#Создание-дополнительных-полей-сущности """

    action = f"/api/v4/{entity.value}/custom_fields"

    data = {
        "type": "text",
        "name": name,
    }

    response = _request_with_token(
        method="POST",
        domain=domain,
        action=action,
        json=data,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return Field.model_validate(response.json())


def get_fields(domain: str, entity: EntityEnum, *, tlogger: TraceLogger) -> list[Field]:
    """ https://www.amocrm.ru/developers/content/crm_platform/custom-fields#Список-полей-сущности """

    action = f"/api/v4/{entity.value}/custom_fields"

    response = _request_with_token(
        method="GET",
        domain=domain,
        action=action,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return [Field.model_validate(f) for f in response.json()["_embedded"]["custom_fields"]]


def _request_with_token(
    method: httpx_helper.MethodType,
    domain: str,
    action: str,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | None = None,
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
    account_id: str,
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
        "session_id": account.cookies_session_id,
        "csrf_token": account.cookies_csrf_token,
        "access_token": account.cookies_access_token,
        "refresh_token": account.cookies_refresh_token,
    }

    if any(v is None for v in cookies_data.values()):
        tlogger.info(f"Some cookies is not defined, got {cookies_data}")
        raise Exception("Not all cookies defined")

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
    method: httpx_helper.MethodType,
    action: str,
    account_id: str | int = "",
    account: amo_models.AmoAccount | None = None,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | None = None,
    headers: dict | None = None,
    retry: bool = False,
    *,
    tlogger: TraceLogger,
):
    account = account or amo_models.AmoAccount.objects.get(amo_id=account_id)
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
        amo_tokens.update_hidden_api_tokens(account_id, tlogger=tlogger)
        return _amojo_request(
            method=method,
            action=action,
            account_id=account_id or account.amo_id,
            params=params,
            data=data,
            json=json,
            headers=headers,
            retry=True,
            tlogger=tlogger,
        )

    return response
