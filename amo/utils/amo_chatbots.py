import amo.models
from amo.utils import amo_pipelines
from utils.logging import TraceLogger


def define_chatbot(account_id: int, lead_id: int, *, tlogger: TraceLogger) -> amo.models.AmoChatBot | None:
    pipeline_status = amo_pipelines.get_pipeline_status_by_lead(account_id, lead_id, tlogger=tlogger)

    if pipeline_status.chat_bot is None:
        tlogger.info(f"Pipeline status '{pipeline_status}' is not linked with chat bot")
        return

    active_chat_bots = amo.models.AmoChatBot.get_available_chat_bots()
    return active_chat_bots.filter(id=pipeline_status.chat_bot.pk).first()
