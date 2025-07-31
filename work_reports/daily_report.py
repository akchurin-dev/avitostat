from datetime import date
from datetime import datetime
from typing import NamedTuple

from django.db.models import Q
from django.db.models import Count

import amo.models
from avito_account.models.models import AvitoAccount
from work_reports.spendings import get_spendings


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


def make_daily_report(since: datetime, until: datetime) -> list[DailyProjectReport]:
    chats_and_contacts = get_chats_and_contacts(since, until)
    spendings = get_spendings(since, until)

    projects_reports = [
        DailyProjectReport(
            project_name=project,
            chats_count=chats_count,
            contacts_count=contacts_count,
            spent_dollars=spendings.get_project_spending(project).spent_dollars,
            spending_per_chat=spendings.get_project_spending(project).spent_dollars / chats_count if chats_count != 0 else None,
            spending_per_contact=spendings.get_project_spending(project).spent_dollars / contacts_count if contacts_count != 0 else None,
        ) for project, chats_count, contacts_count in chats_and_contacts
            if chats_count != 0
    ]
    projects_reports.sort(key=lambda r: r.chats_count, reverse=True)

    return projects_reports


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
                filter=(
                    Q(chatbottask__created_at__range=(since, until))
                    & ~Q(chatbottask__tokens_prompt=0, chatbottask__tokens_completion=0)
                ),
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
                filter=(
                    Q(amochatbottask__created_at__range=(since, until))
                    & ~Q(amochatbottask__tokens_prompt=0, amochatbottask__tokens_completion=0)
                )
            ),
            contacts_count=Count(
                "amochatbottask__chat_id",
                distinct=True,
                filter=(
                    Q(amochatbottask__created_at__range=(since, until), amochatbottask__qualification_achieved=True)
                    & ~Q(amochatbottask__tokens_prompt=0, amochatbottask__tokens_completion=0)
                )
            )
        )
        .values_list("domain", "chats_count", "contacts_count")
    )

    return [
        ChatsAndContacts(
            project_name=project_name,
            chats_count=chats_count,
            contacts_count=contacts_count,
        ) for project_name, chats_count, contacts_count in qs
    ]


def form_daily_report_message_text(report_for_date: date, report: list[DailyProjectReport]) -> str:
    text_parts: list[str] = [f"<b>Отчет за {report_for_date.strftime('%d.%m')} по ИИ-продавцу</b>"]

    for i, project_report in enumerate(report):
        text_parts.append("\n".join([
            f"<b>{i + 1}.</b> {project_report.project_name}",
            f"<b>Переписок:</b> {project_report.chats_count}",
            f"<b>Сделок:</b> {project_report.contacts_count}",
            f"<b>Расход:</b> {round(project_report.spent_dollars, 2)}$",
        ]))

    return "\n\n".join(text_parts)
