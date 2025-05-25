from avito_account.models.models import AvitoAccount
import chat_bot.models


def new_contact_report_sent(account: AvitoAccount, chat_id: str) -> bool:
    return chat_bot.models.ChatBotTask.objects.filter(
        avito_account=account,
        chat_id=chat_id,
        summary_sanded=True,
    ).exists()
