import httpx


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


DEFAULT_TIMEOUT = httpx.Timeout(180, pool=None)
