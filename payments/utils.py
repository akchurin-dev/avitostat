from asgiref.sync import sync_to_async

from avito_account.models.models import AvitoAccount
from base.exceptions import HTTPException
from payments.models import UserProfile


# TODO может стоит перенести в модель профиля?

async def waste_of_balance(avito_account: AvitoAccount, balance_decrease: int):
    user_profile = await sync_to_async(UserProfile.objects.get)(user_id=avito_account.created_by_id)
    user_profile.balance -= balance_decrease
    await user_profile.asave()


@sync_to_async
def check_balance(avito_account):
    balance = avito_account.created_by.userprofile.balance
    if balance < 500:
        print(f"Недостаточно денег - ({balance})")
        raise HTTPException(status_code=400, detail=f"Недостаточно денег - ({balance})")
