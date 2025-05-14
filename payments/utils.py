from django.db.models import F

from avito_account.models.models import User
from base.exceptions import HTTPException
from payments.models import UserProfile
from utils.atomic_async import aatomic


REPORT_DEFAULT_COST = 500


@aatomic()
async def waste_of_balance(user: User, balance_decrease: float) -> None:
    user_profile_qs = UserProfile.objects.filter(user=user)
    user_profile_qs.select_for_update(no_key=True)

    user_profile = await user_profile_qs.aget()

    if user_profile.balance < balance_decrease:
        raise_not_enought_money_exception(
            user=user,
            current_amount=user_profile.balance,
            required_amount=balance_decrease,
        )

    await user_profile_qs.aupdate(balance=F("balance") - balance_decrease)


async def check_balance_enought(
    user: User,
    required_amount: float = REPORT_DEFAULT_COST,
    *,
    raise_exception: bool = True,
) -> bool:

    user_profile = await UserProfile.objects.aget(user=user)
    enought = user_profile.balance >= required_amount

    if not enought and raise_exception:
        raise_not_enought_money_exception(
            user=user,
            current_amount=user_profile.balance,
            required_amount=REPORT_DEFAULT_COST,
        )

    return enought


def raise_not_enought_money_exception(user: User, current_amount: float, required_amount: float) -> None:
    raise HTTPException(
        status_code=400,
        detail=f"User '{user.username}' doesn't have enought money. Current balance {current_amount} but requred {required_amount}",
    )
