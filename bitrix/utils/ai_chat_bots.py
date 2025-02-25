import datetime

from django.db.models import F, Q, QuerySet

from bitrix import models as bitrix_models


# TODO: В дальнейшем функция будет возвращать чат бота по соответствующей воронке

async def define_chat_bot(bitrix_domain: str, dialog_id: int | str) -> bitrix_models.AIChatBot | None:
    chat_bots = bitrix_models.AIChatBot.objects.filter(bitrix_account__domain=bitrix_domain)
    chat_bots = get_available_chat_bots(chat_bots)
    return await chat_bots.afirst()


def get_available_chat_bots[T: bitrix_models.AIChatBotBase](qs: QuerySet[T]) -> QuerySet[T]:
    msk_tz = datetime.timezone(datetime.timedelta(hours=3))
    msk_time_now = datetime.datetime.now(msk_tz).time()

    return qs.filter(
        Q(
            work_time_from__lte=msk_time_now,
            work_time_to__gte=msk_time_now,
        ) | Q(
            Q(work_time_from__lte=msk_time_now) | Q(work_time_to__gte=msk_time_now),
            work_time_from__gte=F("work_time_to"),
        ),
        is_active=True,
    )
