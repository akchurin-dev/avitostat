from datetime import datetime
from datetime import time
from datetime import timedelta
import json
from typing import NamedTuple

from jinja2 import Template
from pathlib import Path
import pdfkit
import sentry_sdk

from avito_account.models.models import AvitoAccount
from base import settings
from base.exceptions import HTTPException
from conversion.utils_week_report import get_text_statistics_report
from messaging.bad_mes_report.statistics.statistics_by_criteria_utils import get_stat_by_criteria_splitted_by_managers
from messaging.bad_mes_report.statistics.total_statistics_utils import get_statistics_total, get_stat_total_splitted_by_managers
from messaging.bad_mes_report.utils_chats import get_ready_chats
from messaging.bad_mes_report.utils_open_ai import messaging_total_analyze, analyze_by_criteria
from messaging.models import ReportMonth
from messaging.utils_duration import get_calls_count_unique_numbers_last_week
from utils.logging import TraceLogger
from utils.miscellaneous import get_tz


class MessaginReport(NamedTuple):
    pdf_path: Path
    tokens: dict | None


async def get_messaging_report_data(
    test_from_prod: bool,
    avito_account_id: int,
    for_api: bool = False,
    period: str = "week",
    *,
    tlogger: TraceLogger,
) -> MessaginReport | None:

    if period not in ["week", "month"]:
        raise ValueError("period must be either 'week' or 'month'")

    avito_account = await AvitoAccount.objects.filter(id=avito_account_id).afirst()

    if avito_account is None:
        raise HTTPException(status_code=404, detail="error: Аккаунт Avito не найден")

    analyze_all_chats = {
        "avito_account_name": avito_account.name,
        "avito_account_id": avito_account.pk,
    }

    try:
        chats_filtered_by_excluded_sellings, all_chats = await get_ready_chats(avito_account, period=period)

        if len(chats_filtered_by_excluded_sellings) == 0:
            raise HTTPException(status_code=404, detail="Нет чатов для анализа")

        tlogger.info(f"Found {len(all_chats)} chats")
        tlogger.info(f"Found {len(chats_filtered_by_excluded_sellings)} chats filtered by excluded sellings")

        analyze_all_chats["chats_for_analyze"] = len(chats_filtered_by_excluded_sellings)
        analyze_all_chats["chats_without_filtering_count"] = len(all_chats)
        await add_start_end_dates(analyze_all_chats, period)

        #  Total statistics
        statistics_total = await get_statistics_total(chats_filtered_by_excluded_sellings)
        if statistics_total:
            analyze_all_chats["statistics_total"] = statistics_total

        statistics_new = await get_text_statistics_report(avito_account=avito_account, period=period)
        calls_unique_users = get_calls_count_unique_numbers_last_week(avito_account, tlogger=tlogger)
        if statistics_new:
            analyze_all_chats["contacts"] = {
                "total": (len(all_chats) + calls_unique_users) or 0,
                "chats_without_filtering_count": len(all_chats) or 0,
                "chats_at_scheduler_time": len(all_chats) or 0,
                "calls_unique_users": calls_unique_users or 0,
                "contacts_requested": statistics_new["total_metrics"].get("total_contacts_count"),
                "total_favorites_count": statistics_new["total_metrics"].get("total_favorites_count"),
                "total_conversion_count": statistics_new["total_metrics"].get("total_conversion_count"),
            }

        stat_splitted_by_managers = await get_stat_total_splitted_by_managers(chats_filtered_by_excluded_sellings)
        if stat_splitted_by_managers:
            analyze_all_chats["statistics_by_managers"] = stat_splitted_by_managers

        analyze_messaging = await messaging_total_analyze(avito_account, chats_filtered_by_excluded_sellings, period)
        if analyze_messaging:
            analyze_all_chats["chats"] = analyze_messaging

        analyze_by_criteria_raw_res = await analyze_by_criteria(chats_filtered_by_excluded_sellings, test_from_prod, avito_account)
        if analyze_by_criteria_raw_res:
            analyze_by_crit_split_by_man = await get_stat_by_criteria_splitted_by_managers(chats_filtered_by_excluded_sellings)
            analyze_all_chats["analyze_by_criteria"] = analyze_by_crit_split_by_man

    except Exception as e:
        sentry_sdk.capture_exception(e)
        tlogger.error(e)
        raise e

    tokens = None
    if analyze_by_criteria_raw_res:
        tokens = await get_tokens_information(analyze_by_criteria_raw_res, tlogger=tlogger)

    if analyze_all_chats:
        analyze_all_chats = chats_timestamp_to_datetime(analyze_all_chats)

    if for_api and analyze_all_chats:  # Этот блок кода чтобы облегчить жэсонины
        await api_report_data_generation(analyze_all_chats, avito_account)
        return None

    pdf_path = await get_pdf_report(avito_account_id, analyze_all_chats)

    return MessaginReport(pdf_path, tokens)


async def api_report_data_generation(analyze_all_chats: dict, avito_account: AvitoAccount) -> None:
    chats = analyze_all_chats.get("chats", None)
    if chats is not None:
        for chat in chats:
            messages = chat.get("messages", [])
            if len(messages) > 15:
                chat["messages"] = messages[:15]

    current_month = datetime.now().month
    # данная сериализация для того чтобы datetime в текст менять
    serialized_report_data = json.dumps(analyze_all_chats, ensure_ascii=False, cls=date_objects_to_json_encoder)
    await ReportMonth.objects.acreate(
        month=current_month,
        account=avito_account,
        data=serialized_report_data,
    )


class date_objects_to_json_encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, time)):
            return obj.isoformat()  # Преобразование в строку формата ISO 8601
        return super().default(obj)


async def add_start_end_dates(analyze_all_chats, period: str) -> dict:
    if period == "week":
        start_date = (datetime.now() - timedelta(days=7)).strftime("%d.%m.%Y")
    if period == "month":
        start_date = (datetime.now() - timedelta(days=30)).strftime("%d.%m.%Y")

    end_date = datetime.now().strftime("%d.%m.%Y")
    analyze_all_chats["start_date"] = start_date
    analyze_all_chats["end_date"] = end_date
    return analyze_all_chats


def chats_timestamp_to_datetime(analyze_all_chats):
    try:
        msk_tz = get_tz(utc_offset_hours=3)

        for chat in analyze_all_chats.get("chats"):
            timestamp = chat.get("updated")
            chat["updated_date"] = datetime.fromtimestamp(timestamp, msk_tz).strftime('%d.%m.%Y')

            for message in chat.get("messages", []):
                timestamp = message.get("created")
                message["created_time"] = datetime.fromtimestamp(timestamp, msk_tz).time()

        return analyze_all_chats
    except:
        raise


async def get_pdf_report(avito_account_id, analyze_all_chats):
    if settings.ENVIRONMENT == 'DEVELOPMENT':
        wkhtmltopdf_path = "/usr/local/bin/wkhtmltopdf"  # For testing 5 items  for economy
    else:
        wkhtmltopdf_path = "/usr/bin/wkhtmltopdf"

    html_content = await bad_messaging_report_generate_html(analyze_all_chats=analyze_all_chats)
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    # Define the directory and file path with the date
    reports_dir = Path("messaging/bad_mes_report/PDFs")
    reports_dir.mkdir(parents=True, exist_ok=True)
    # Get the current date in dd.mm.yyyy format
    current_date = datetime.now().strftime("%d.%m.%Y")
    pdf_path = reports_dir / f"bad_mes_report_{current_date}_{avito_account_id}.pdf"
    pdfkit.from_string(html_content, pdf_path, configuration=config)
    return pdf_path


async def bad_messaging_report_generate_html(analyze_all_chats):
    # Загрузка шаблона из файла
    with open("messaging/templates/messaging/bad_messaging_report.html", "r", encoding="utf-8") as file:
        template_content = file.read()

    template = Template(template_content)

    # Данные для подстановки в шаблон

    avito_account_name = analyze_all_chats['avito_account_name'] if analyze_all_chats else "Неизвестно"

    # Генерация HTML с использованием шаблона и данных
    return template.render(
        avito_account_name=avito_account_name,
        start_date=analyze_all_chats.get('start_date'),
        end_date=analyze_all_chats.get('end_date'),
        contacts=analyze_all_chats.get('contacts'),
        chats=analyze_all_chats.get('chats', []),
        statistics_total=analyze_all_chats.get("statistics_total"),
        statistics_by_managers=analyze_all_chats.get("statistics_by_managers"),
        analyze_by_criteria=analyze_all_chats.get("analyze_by_criteria"),
    )


async def get_tokens_information(analyze_by_criteria_raw_result: list, *, tlogger: TraceLogger):
    # BY CRITERIA
    by_criteria_completion = [x["tokens_by_criteria_analyze"].get("completion_tokens")
                              for x in analyze_by_criteria_raw_result]
    by_criteria_prompt = [x["tokens_by_criteria_analyze"].get("prompt_tokens")
                          for x in analyze_by_criteria_raw_result]

    # TOTAL ANALYZE
    total_analyze_completion = [x.get("tokens_total_analyze", None).get("completion_tokens")
                                for x in analyze_by_criteria_raw_result if x.get("tokens_total_analyze", None) is not None]
    total_analyze_prompt = [x.get("tokens_total_analyze", None).get("prompt_tokens")
                            for x in analyze_by_criteria_raw_result if x.get("tokens_total_analyze", None) is not None]

    total_completion = sum(total_analyze_completion) + sum(by_criteria_completion)
    total_prompt = sum(by_criteria_prompt) + sum(total_analyze_prompt)

    tlogger.info(f"Всего токенов completion {round(total_completion, 2)}")
    tlogger.info(f"Всего токенов prompt {round(total_prompt, 2)}")
    tlogger.info(
        f"Среднее количество токенов completion на чат {round(total_completion / len(analyze_by_criteria_raw_result), 2)}")
    tlogger.info(f"Всего количество токенов prompt на чат {round(total_prompt / len(analyze_by_criteria_raw_result), 2)}")
    tlogger.info(f"Чатов обработано {len(analyze_by_criteria_raw_result)}")

    return {
        "completion": total_completion,
        "prompt": total_prompt
    }
