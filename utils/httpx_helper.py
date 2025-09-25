from typing import Literal

import httpx

from utils.logging import TraceLogger


MethodType = Literal["GET", "POST", "PATCH", "DELETE", "HEAD"]

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
    json: dict | list | None = None,
    headers: dict | None = None,
    timeout_retries: int = 3,
    tlogger: TraceLogger | None = None,
) -> httpx.Response:

    tlogger = tlogger or TraceLogger()

    error = None

    for i in range(timeout_retries + 1):
        try:
            if i > 1:
                tlogger.info(f"Try again request to {url}")

            response = httpx.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
            )
            break
        except httpx.TimeoutException as e:
            error = e
            tlogger.info(f"Timeout exception when request to {url}")
    else:
        assert error is not None
        raise error

    if not response.is_success:
        log_about_not_success_response(response, tlogger)

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


def log_about_not_success_response(response: httpx.Response, tlogger: TraceLogger) -> None:
    tlogger.info({"Not success response": [
        ("url", response.url),
        ("status_code", response.status_code),
        ("response_data", response.text[:500]),
        ("request_data", response.request.content.decode()),
    ]})
