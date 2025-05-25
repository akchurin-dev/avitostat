from avito_account.models.models import AvitoAccount
from chat_bot import ai_utils
import chat_bot.models
from utils.logging import TraceLogger


def new_contact_report_sent(account: AvitoAccount, chat_id: str) -> bool:
    return chat_bot.models.ChatBotTask.objects.filter(
        avito_account=account,
        chat_id=chat_id,
        summary_sanded=True,
    ).exists()


def may_send_report(chatbot: chat_bot.models.AiChatBot, contacts: ai_utils.AIAnswerContacts | None, *, tlogger: TraceLogger) -> bool:
    if not chatbot.send_new_contact_report:
        tlogger.info("Chatbot configured don't send new contacts reports")
        return False

    if not contacts:
        tlogger.info(f"Contacts not found, got {contacts}")
        return False

    tlogger.info({
        "mobile": contacts.mobile,
        "whatsapp": contacts.whatsapp,
        "telegram": contacts.telegram,
    })

    if contacts.mobile or contacts.whatsapp or contacts.telegram:
        tlogger.info("May send report")
        return True

    tlogger.info("Don't have required contacts for report sending")

    return False
