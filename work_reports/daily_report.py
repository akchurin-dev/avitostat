from datetime import datetime
from typing import NamedTuple

from django.db.models import Q
from django.db.models import Count

import ai_requests.models
import amo.models
import chat_bot.models
from avito_account.models.models import AvitoAccount


class TokensCoast(NamedTuple):
    dollars_per_mil_input_tokens: float
    dollars_per_mil_output_tokens: float


MODELS_TO_COASTS: dict[str, TokensCoast] = {
    "gpt-4.1-2025-04-14": TokensCoast(2, 8),
    "gpt-4o-2024-08-06": TokensCoast(5, 20),
}


class DailyProjectReport(NamedTuple):
    project_name: str
    chats_count: int
    contacts_count: int
    spent_dollars: float
    spending_per_chat: float | None
    spending_per_contact: float | None


class ChatsAndContacts(NamedTuple):
    project_name: str
    chats_count: int
    contacts_count: int


class Spending(NamedTuple):
    project_name: str
    spent_dollars: float


def make_daily_report(since: datetime, until: datetime) -> list[DailyProjectReport]:
    chats_and_contacts = get_chats_and_contacts(since, until)
    project_to_spending = {p.project_name: p for p in get_spending(since, until)}

    return [
        DailyProjectReport(
            project_name=project,
            chats_count=chats_count,
            contacts_count=contacts_count,
            spent_dollars=project_to_spending[project].spent_dollars,
            spending_per_chat=project_to_spending[project].spent_dollars / chats_count if chats_count != 0 else None,
            spending_per_contact=project_to_spending[project].spent_dollars / contacts_count if contacts_count != 0 else None,
        ) for project, chats_count, contacts_count in chats_and_contacts
    ]


def get_chats_and_contacts(since: datetime, until: datetime) -> list[ChatsAndContacts]:
    return get_avito_chats_and_contacts(since, until) + get_amo_chats_and_contacts(since, until)


def get_avito_chats_and_contacts(since: datetime, until: datetime) -> list[ChatsAndContacts]:
    qs = (
        AvitoAccount.objects
        .values("name")
        .annotate(
            chats_count=Count(
                "chatbottask__chat_id",
                distinct=True,
                filter=Q(chatbottask__created_at__range=(since, until))
            ),
            contacts_count=Count(
                "chatbottask__chat_id",
                distinct=True,
                filter=Q(
                    chatbottask__created_at__range=(since, until),
                    chatbottask__mobile__isnull=False
                )
            )
        )
        .order_by("-chats_count")
        .values_list("name", "chats_count", "contacts_count")
    )

    return [
        ChatsAndContacts(
            project_name=project,
            chats_count=chats_count,
            contacts_count=contacts_count,
        ) for project, chats_count, contacts_count in qs
    ]


def get_amo_chats_and_contacts(since: datetime, until: datetime) -> list[ChatsAndContacts]:
    qs = (
        amo.models.AmoAccount.objects
        .values("domain")
        .annotate(
            chats_count=Count(
                "amochatbottask__chat_id",
                distinct=True,
                filter=Q(
                    ~Q(amochatbottask__tokens_prompt=0, amochatbottask__tokens_completion=0),
                    amochatbottask__created_at__range=(since, until),
                )
            ),
        )
        .values_list("domain", "chats_count")
    )

    return [
        ChatsAndContacts(
            project_name=project_name,
            chats_count=chats_count,
            contacts_count=0,
        ) for project_name, chats_count in qs
    ]


def get_spending(since: datetime, until: datetime) -> list[Spending]:
    qs = ai_requests.models.AIRequest.objects.filter(
        created_at__range=(since, until),
        tag__isnull=False,
    )

    model_to_project_tokens_spending: dict[str, dict[str, tuple[float, float]]] = {}

    for ai_request in qs:
        if ai_request.model not in model_to_project_tokens_spending:
            model_to_project_tokens_spending[ai_request.model] = {}

        if ai_request.tag.count("|") != 2:
            continue

        project = ai_request.tag.split("|")[1].strip()
        tokens_spending = model_to_project_tokens_spending[ai_request.model].get(project, (0, 0))

        model_to_project_tokens_spending[ai_request.model][project] = (
            tokens_spending[0] + ai_request.tokens_prompt,
            tokens_spending[1] + ai_request.tokens_completion,
        )

    project_to_dollars_spending: dict[str, float] = {}

    for model in model_to_project_tokens_spending:
        tokens_coast = MODELS_TO_COASTS.get(model, TokensCoast(0, 0))
        for project, (tokens_prompt, tokens_completion) in model_to_project_tokens_spending[model].items():
            project_to_dollars_spending[project] = sum([
                project_to_dollars_spending.get(project, 0),
                tokens_prompt * tokens_coast.dollars_per_mil_input_tokens / 10 ** 6,
                tokens_completion * tokens_coast.dollars_per_mil_output_tokens / 10 ** 6
            ])

    return [Spending(project, spent_dollars) for project, spent_dollars in project_to_dollars_spending.items()]


def form_daily_report_message_text(report: list[DailyProjectReport]) -> str:
    text_parts: list[str] = []

    for i, project_report in enumerate(report):
        text_parts.append("\n".join([
            f"<b>{i + 1}.</b> {project_report.project_name}",
            f"<b>Переписок:</b> {project_report.chats_count}",
            f"<b>Сделок:</b> {project_report.contacts_count}",
            f"<b>Расход:</b> {project_report.spent_dollars}",
        ]))

    return "\n\n".join(text_parts)
