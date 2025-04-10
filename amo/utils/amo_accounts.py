from amo import models as amo_models
from amo.utils import amo_api
from amo.utils import amo_tokens
from utils.logging import TraceLogger


def create_account_or_update_tokens(domain: str, code: str, created_by_id: int, *, tlogger: TraceLogger) -> amo_models.AmoAccount:
    tokens = amo_tokens.get_tokens(
        domain=domain,
        code=code,
        tlogger=tlogger,
    )
    account_info = amo_api.get_account_info(
        domain=domain,
        access_token=tokens.access_token,
        tlogger=tlogger,
    )

    account, created = amo_models.AmoAccount.objects.update_or_create(
        amo_id=account_info.id,
        domain=domain,
        amojo_id=account_info.amojo_id,
        defaults={
            "name": account_info.name,
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "created_by_id": created_by_id,
        },
    )

    amo_tokens.update_hidden_api_tokens(account.amo_id, tlogger=tlogger)

    if created:
        amo_api.subscribe_to_new_messages(
            domain=domain,
            tlogger=tlogger,
        )
        tlogger.info(f"Create new AmoAccount with domain='{domain}'")
    else:
        tlogger.info(f"Update tokens in AmoAccount (domain='{domain}')")

    return account
