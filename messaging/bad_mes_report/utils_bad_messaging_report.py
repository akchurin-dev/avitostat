import pdfkit
import sentry_sdk
from avito_account.models.models import AvitoAccount
from base import settings
from base.exceptions import HTTPException
from jinja2 import Template
from asgiref.sync import sync_to_async
from pathlib import Path
from datetime import datetime, timedelta

from conversion.utils_week_report import get_text_statistics_report
from messaging.api import get_calls_statistic_last_week
from messaging.bad_mes_report.statistics.statistics_by_criteria_utils import \
    get_stat_by_criteria_splitted_by_managers
from messaging.bad_mes_report.statistics.total_statistics_utils import get_statistics_total, \
    get_stat_total_splitted_by_managers
from messaging.bad_mes_report.utils_chats import get_ready_chats
from messaging.bad_mes_report.utils_open_ai import messaging_total_analyze, analyze_by_criteria
from messaging.utils_duration import get_calls_count_unique_users_last_week


async def get_messaging_week_report_pdf(avito_account_id, test_from_prod: bool):
    avito_account = await sync_to_async(AvitoAccount.objects.filter(id=avito_account_id).last)()
    if avito_account:
        analyze_all_chats = {"avito_account_name": avito_account.name, "avito_account_id": avito_account.id, }
        try:
            ready_chats, chats_without_filtering_count = await get_ready_chats(avito_account)
            # PROCESSING WITH FILTERED CHATS
            if len(ready_chats) < 2:
                raise HTTPException(status_code=404, detail="Нет чатов для анализа, или их менее двух")
                # return False
            else:
                analyze_all_chats["chats_for_analyze"] = len(ready_chats)
                analyze_all_chats["chats_without_filtering_count"] = chats_without_filtering_count

            # Checking count of messages for analytics
            if settings.ENVIRONMENT == 'DEVELOPMENT' or test_from_prod:
                ready_chats = ready_chats[:10]  # For testing 5items for economy

            #  Total statistics
            statistics_total = await get_statistics_total(ready_chats)
            if statistics_total:
                analyze_all_chats["header_with_statistics"] = statistics_total

            calls_unique_users = await get_calls_count_unique_users_last_week(avito_account)
            if chats_without_filtering_count:
                analyze_all_chats["contacts"] = {
                    "total": (chats_without_filtering_count + calls_unique_users) or 0,
                    "chats_without_filtering_count": chats_without_filtering_count or 0,
                    "chats_at_scheduler_time": len(ready_chats) or 0,
                    "calls_unique_users": calls_unique_users or 0
                }

            stat_splitted_by_managers = await get_stat_total_splitted_by_managers(ready_chats)
            if stat_splitted_by_managers:
                analyze_all_chats["statistics_splitted_by_managers"] = stat_splitted_by_managers

            analyze_messaging = await messaging_total_analyze(ready_chats, test_from_prod, avito_account)
            if analyze_messaging:
                analyze_all_chats["chats"] = analyze_messaging

            analyze_by_criteria_raw_res = await analyze_by_criteria(ready_chats, test_from_prod, avito_account)
            if analyze_by_criteria_raw_res:
                analyze_by_crit_split_by_man = await get_stat_by_criteria_splitted_by_managers(ready_chats)
                analyze_all_chats["analyze_by_criteria"] = analyze_by_crit_split_by_man

        except Exception as send_error:
            sentry_sdk.capture_exception(send_error)
            print(send_error)
            raise send_error
            # return False
        else:
            analyze_all_chats["compared_messages"] = "Чаты не найдены"

        # tokens counting
        tokens = None
        if analyze_by_criteria_raw_res:
            tokens = await get_tokens_information(analyze_by_criteria_raw_res)

        if analyze_all_chats:
            analyze_all_chats = await converting_created_timestamp_to_datetime(analyze_all_chats)

        return await get_pdf_report(avito_account_id, analyze_all_chats), tokens
    else:
        raise HTTPException(status_code=404, detail="error: Аккаунт Avito не найден")


async def converting_created_timestamp_to_datetime(analyze_all_chats):
    try:
        for chat in analyze_all_chats.get("chats"):
            timestamp = chat.get("created")
            chat["created_date"] = datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y')
            for message in chat.get("messages"):
                timestamp = message.get("created")
                message["created_time"] = datetime.fromtimestamp(timestamp).time()
        return analyze_all_chats
    except Exception:
        raise Exception


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
    start_date = (datetime.now() - timedelta(days=6)).strftime("%d.%m.%Y")
    end_date = datetime.now().strftime("%d.%m.%Y")
    avito_account_name = analyze_all_chats['avito_account_name'] if analyze_all_chats else "Неизвестно"

    # Генерация HTML с использованием шаблона и данных
    return template.render(avito_account_name=avito_account_name,
                           start_date=start_date,
                           end_date=end_date,
                           contacts=analyze_all_chats.get('contacts'),
                           chats=analyze_all_chats.get('chats', []),
                           statistics_total=analyze_all_chats.get("header_with_statistics"),
                           statistics_by_managers=analyze_all_chats.get("statistics_splitted_by_managers"),
                           analyze_by_criteria=analyze_all_chats.get("analyze_by_criteria"), )


async def get_tokens_information(analyze_by_criteria_raw_result: list):
    # BY CRITERIA
    by_criteria_completion = [x["tokens_by_criteria_analyze"].get("completion_tokens") for x in
                              analyze_by_criteria_raw_result]
    by_criteria_prompt = [x["tokens_by_criteria_analyze"].get("prompt_tokens") for x in analyze_by_criteria_raw_result]

    # TOTAL ANALYZE
    total_analyze_completion = [x["tokens_total_analyze"].get("completion_tokens") for x in
                                analyze_by_criteria_raw_result]
    total_analyze_prompt = [x["tokens_total_analyze"].get("prompt_tokens") for x in analyze_by_criteria_raw_result]

    total_completion = sum(total_analyze_completion) + sum(by_criteria_completion)
    total_prompt = sum(by_criteria_prompt) + sum(total_analyze_prompt)

    print(f"Всего токенов completion {total_completion}")
    print(f"Всего токенов prompt {total_prompt}")
    print(f"Среднее количество токенов completion на чат {total_completion / len(analyze_by_criteria_raw_result)}")
    print(f"Всего количество токенов prompt на чат {total_prompt / len(analyze_by_criteria_raw_result)}")
    print(f"Чатов обработано {len(analyze_by_criteria_raw_result)}")

    return {
        "completion": total_completion,
        "prompt": total_prompt
    }
