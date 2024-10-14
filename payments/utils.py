from asgiref.sync import sync_to_async

from avito_account.models.models import AvitoAccount
from payments.models import UserProfile


async def waste_of_balance(avito_account: AvitoAccount, balance_decrease: int):
    user_profile = await sync_to_async(UserProfile.objects.get)(user_id=avito_account.created_by_id)
    user_profile.balance -= balance_decrease
    await user_profile.asave()
