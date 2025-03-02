from bitrix import models as bitrix_models


def create_bitrix_account(domain: str, owner_id: int, access_token: str, refresh_token: str):
    account, _ = bitrix_models.BitrixAccount.objects.update_or_create(
        domain=domain,
        defaults={
            "owner_id": owner_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )

    return account


def get_bitrix_account(domain: str, raise_not_exist_exception=False):
    account = bitrix_models.BitrixAccount.objects.filter(domain=domain)

    if raise_not_exist_exception:
        return account.get()

    return account.first()


def update_tokens(bitrix_domain: str, access_token: str, refresh_token: str):
    account = bitrix_models.BitrixAccount.objects.filter(domain=bitrix_domain)
    account.update(
        access_token=access_token,
        refresh_token=refresh_token,
    )
