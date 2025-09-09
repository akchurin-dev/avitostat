from datetime import datetime
from typing import NamedTuple

from django.db.models import Count
from django.db.models import Q

import amo.models
from avito_account.models.models import AvitoAccount
from work_reports.spendings import get_spendings


class MonthlyReportByProject(NamedTuple):
    project_name: str
    spending: float
    answers_count: int


def make_monthly_report(since: datetime, until: datetime) -> list[MonthlyReportByProject]:
    spendings = get_spendings(since, until)

    projects_to_messages_count = get_answers_count_by_avito_projects(since, until)
    projects_to_messages_count.update(get_answers_count_by_amo_projects(since, until))

    projects_reports = [
        MonthlyReportByProject(
            project_name=project,
            spending=spendings.get_project_spending(project).spent_dollars,
            answers_count=messages_count,
        ) for project, messages_count in projects_to_messages_count.items()
    ]
    projects_reports = [pr for pr in projects_reports if pr.answers_count > 0 or pr.spending > 0]
    projects_reports.sort(key=lambda pr: pr.answers_count, reverse=True)

    return projects_reports


def get_answers_count_by_avito_projects(since: datetime, until: datetime) -> dict[str, int]:
    qs = (
        AvitoAccount.objects
        .filter(
            Q(chatbottask__message_id__isnull=True)
            | Q(chatbottask__created_at__range=[since, until])
        )
        .annotate(
            answers_count=Count(
                "chatbottask",
                filter=Q(
                    chatbottask__message_id__isnull=False,
                    chatbottask__answer_text__isnull=False,
                )
                & ~Q(chatbottask__answer_text=""),
            )
        )
        .values_list("id", "name", "answers_count")
    )

    return {project_name: answers_count for _, project_name, answers_count in qs}


def get_answers_count_by_amo_projects(since: datetime, until: datetime) -> dict[str, int]:
    qs = (
        amo.models.AmoAccount.objects
        .filter(
            Q(amochatbottask__id__isnull=True)
            | Q(amochatbottask__created_at__range=[since, until])
        )
        .annotate(
            answers_count=Count(
                "amochatbottask",
                filter=Q(
                    amochatbottask__answer_text__isnull=False,
                ) & ~Q(amochatbottask__answer_text="")
            )
        )
        .values_list("amo_id", "domain", "answers_count")
    )

    return {domain: answers_count for _, domain, answers_count in qs}


def get_monthly_report_message_text(since: datetime, until: datetime, projects_reports: list[MonthlyReportByProject]) -> str:
    parts: list[str] = [
        f"Отчет с <b>{since.strftime('%d/%m/%Y')}</b> по <b>{until.strftime('%d/%m/%Y')}</b>",
    ]

    for i, project_report in enumerate(projects_reports):
        parts.append("\n".join([
            f"<b>{i + 1}.</b> {project_report.project_name}",
            f"<b>Расход:</b> {round(project_report.spending, 2)}$",
            f"<b>Отправлено сообщений:</b> {project_report.answers_count}",
        ]))

    return "\n\n".join(parts)
