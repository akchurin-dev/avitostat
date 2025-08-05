import chat_bot.models
from chat_bot.tasks import dialog_trigger_launcher
from utils.logging import TraceLogger


def initiate_trigger_condition_check(
    task: chat_bot.models.ChatBotTask,
    chatbot: chat_bot.models.AiChatBot,
    last_message_id: str,
    *,
    tlogger: TraceLogger,
) -> None:

    worked_triggers = chat_bot.models.WorkedTrigger.get_worked_triggers_by_chat(task.avito_account, task.chat_id)

    next_trigger: chat_bot.models.DialogTrigger | None = None
    delay = 0

    if len(worked_triggers) != 0:
        tlogger.info(f"Last worked trigger is '{worked_triggers[-1].trigger.title}'")
        next_trigger = worked_triggers[-1].trigger.trigger
        delay = worked_triggers[-1].trigger.delay_before_launch_trigger_sec
    else:
        tlogger.info("Worked triggers not found")
        next_trigger = chatbot.trigger
        delay = chatbot.delay_before_launch_trigger_sec

    if next_trigger is None:
        tlogger.info("Next trigger not found")
        return

    tlogger.info(f"Next trigger is '{next_trigger.title}'")

    dialog_trigger_launcher.s(
    # dialog_trigger_launcher(
        trigger_id=next_trigger.pk,
        chat_id=task.chat_id,
        last_message_id=last_message_id,
        trace_id=tlogger.trace_id,
    ).apply_async(countdown=delay)
    # )
