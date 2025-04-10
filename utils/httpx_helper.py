from typing import Literal

import httpx

from utils.logging import TraceLogger


MethodType = Literal["GET", "POST", "PATCH", "DELETE"]

DEFAULT_TIMEOUT = httpx.Timeout(15, pool=None)


def create_client(
    verify: bool = True,
    timeout: httpx.Timeout | None = None,
    base_url: str = "",
    max_connections: int | None = 100,
    max_keepalive_connections: int | None = 20,
    keepalive_expiry: float | None = 5,
    retries: int = 20,
) -> httpx.Client:

    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
        keepalive_expiry=keepalive_expiry,
    )

    transport = httpx.HTTPTransport(
        verify=verify,
        limits=limits,
        retries=retries,
    )

    return httpx.Client(
        verify=verify,
        timeout=timeout or DEFAULT_TIMEOUT,
        limits=limits,
        base_url=base_url,
        transport=transport,
    )


def request(
    method: MethodType,
    url: str,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | None = None,
    headers: dict | None = None,
    tlogger: TraceLogger | None = None,
) -> httpx.Response:

    tlogger = tlogger or TraceLogger()

    response = httpx.request(
        method=method,
        url=url,
        params=params,
        data=data,
        json=json,
        headers=headers,
    )

    if not response.is_success:
        tlogger.info((
            f"Not success response when request '{url}'. "
            f"Got status={response.status_code}, data={response.text[:500]}"
        ))

    return response


def add_bearer(headers: dict | None, token: str) -> dict:
    return add_header(headers, key="Authorization", value="Bearer " + token)


def add_header(headers: dict | None, key: str, value) -> dict:
    if headers is None:
        headers = {}
    else:
        headers = headers.copy()

    headers[key] = value
    return headers
