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
