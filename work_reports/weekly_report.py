from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import NamedTuple

from django.db.models import Count
from django.db.models import Q

from avito_account.models.models import AvitoAccount
from work_reports.spendings import Spendings
from work_reports.spendings import get_spendings


class WeeklyReport(NamedTuple):
    active_projects_count: int
    successfull_report_sendings: int
    projects_with_unsuccessfull_report_sending: list[str]
    total_spending: float
    spendings: Spendings


def make_weekly_report(since: datetime, until: datetime, find_reports_at_date: date) -> WeeklyReport:
    active_projects = get_active_projects()
    successfull_report_projects, unsuccessfull_report_projects = get_successfull_unsuccessfull_report_projects(find_reports_at_date)
    spendings = get_spendings(since, until)

    return WeeklyReport(
        active_projects_count=len(active_projects),
        successfull_report_sendings=len(successfull_report_projects),
        projects_with_unsuccessfull_report_sending=[p for p in unsuccessfull_report_projects if p in active_projects],
        total_spending=sum(s.spent_dollars for s in spendings),
        spendings=spendings,
    )


def get_active_projects() -> list[str]:
    return list(
        AvitoAccount.objects
        .filter(aichatbot__is_active=True)
        .values_list("name", flat=True)
    )


def get_successfull_unsuccessfull_report_projects(day: date) -> tuple[list[str], list[str]]:
    qs = (
        AvitoAccount.objects.annotate(
            success=Count(
                "sendingreport",
                filter=Q(
                    sendingreport__timestamp__date=day,
                    sendingreport__campaign__name="weekly",
                    sendingreport__campaign__sending_type="PDF",
                    sendingreport__success=True,
                )
            ),
        )
        .values_list("name", "success")
    )

    return (
        [project for project, success in qs if success > 0],
        [project for project, success in qs if success == 0],
    )


def get_weekly_report_message_text(report: WeeklyReport) -> str:
    text_parts: list[str] = ["<b>Отчет по отправленным отчетам ✅</b>"]

    text_part = f"<b>Проектов в системе:</b> {report.active_projects_count}"
    text_part += "✅" if report.active_projects_count > 0 else "⚠️"
    text_parts.append(text_part)

    text_parts.append("")

    text_part = f"<b>Отправлен отчет клиентам:</b> {report.successfull_report_sendings}"
    text_part += "✅" if report.successfull_report_sendings > 0 else "⚠️"
    text_parts.append(text_part)

    text_part = f"<b>Не отправлено:</b> {len(report.projects_with_unsuccessfull_report_sending)}"
    text_part += "✅" if len(report.projects_with_unsuccessfull_report_sending) == 0 else "⚠️"
    text_parts.append(text_part)

    text_parts.append("")

    if len(report.projects_with_unsuccessfull_report_sending) != 0:
        text_parts.extend(report.projects_with_unsuccessfull_report_sending)
        text_parts.append("")

    text_parts.append("")

    text_parts.append(f"<b>Расход</b> в неделю. ChatGPT: {round(report.total_spending, 2)}$")

    text_parts.append("")
    text_parts.append("ТОП 5 по расходу:")
    text_parts.append("")
    text_parts.extend([f"{s.project_name}: {round(s.spent_dollars, 2)}$" for s in report.spendings][:5] or ["Расходы не найдены"])

    return "\n".join(text_parts)
