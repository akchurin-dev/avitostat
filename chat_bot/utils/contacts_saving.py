from chat_bot.ai_utils import AIAnswerWithContacts
from chat_bot.models import ChatBotTask
from chat_bot.models import CompanyBranch


def task_contacts_save(
    new_task: ChatBotTask,
    ai_answer: AIAnswerWithContacts,
    is_incoming: bool,
    company_branch: CompanyBranch | None,
) -> None:

    new_task.is_incoming = is_incoming
    new_task.answer_text = ai_answer.answer
    new_task.company_branch = None

    if company_branch:
        new_task.company_branch = company_branch

    if new_task.company_branch is None and ai_answer.nearest_company_branch:
        new_task.company_branch = CompanyBranch.objects.filter(
            account = new_task.avito_account,
            location_slug=ai_answer.nearest_company_branch,
        ).first()

    new_task.tokens_completion = ai_answer.tokens_completion
    new_task.tokens_prompt = ai_answer.tokens_prompt

    if ai_answer.contacts:
        new_task.address = ai_answer.contacts.address
        new_task.mobile = ai_answer.contacts.mobile
        new_task.whatsapp = ai_answer.contacts.whatsapp
        new_task.telegram = ai_answer.contacts.telegram
        new_task.email = ai_answer.contacts.email

    new_task.save()
