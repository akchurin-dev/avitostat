from bitrix import models as bitrix_models


async def create_bitrix_account(domain: str, owner_id: int, access_token: str, refresh_token: str):
    account, _ = await bitrix_models.BitrixAccount.objects.aupdate_or_create(
        domain=domain,
        defaults={
            "owner_id": owner_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )

    return account


async def get_bitrix_account(domain: str, raise_not_exist_exception=False):
    account = bitrix_models.BitrixAccount.objects.filter(domain=domain)

    if raise_not_exist_exception:
        return await account.aget()

    return await account.afirst()


async def update_tokens(bitrix_domain: str, access_token: str, refresh_token: str):
    account = bitrix_models.BitrixAccount.objects.filter(domain=bitrix_domain)
    await account.aupdate(
        access_token=access_token,
        refresh_token=refresh_token,
    )
