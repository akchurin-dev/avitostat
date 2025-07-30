from datetime import datetime
from typing import NamedTuple

from work_reports.spendings import Spendings


class WeeklyReport(NamedTuple):
    active_projects_count: int
    successfull_report_sendings: int
    projects_with_unsuccessfull_report_sending: list[str]
    total_spending: float
    spendings: Spendings


def make_weekly_report(since: datetime, until: datetime) -> WeeklyReport:
    pass


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

    text_parts.append(f"<b>Расход</b> в неделю. ChatGPT: {report.total_spending}$")

    text_parts.append("")
    text_parts.append("ТОП 5 по расходу:")
    text_parts.append("")
    text_parts.extend([f"{s.project_name}: {s.spent_dollars}$" for s in report.spendings] or ["Расходы не найдены"])

    return "\n".join(text_parts)
