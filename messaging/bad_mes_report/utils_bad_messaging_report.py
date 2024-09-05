import os

import pdfkit
import sentry_sdk
from dotenv import load_dotenv

from avito_account.models import AvitoAccount, WorkSchedule, moscow_time, MOSCOW_TZ
from exceptions import HTTPException
from messaging.api import get_chats, get_chats_messages
from jinja2 import Template
from asgiref.sync import sync_to_async
from pathlib import Path
from datetime import datetime, time, timedelta

from messaging.bad_mes_report.statistics.statistics_by_criteria_utils import \
    get_stat_by_crit_split_by_man
from messaging.bad_mes_report.statistics.total_statistics_utils import get_statistics_total, \
    get_stat_total_split_by_man
from messaging.bad_mes_report.utils_open_ai import messaging_total_analyze, analyze_by_criteria
from messaging.views import get_chats_for_last_week
import re
import pytz

load_dotenv()
ENVIRONMENT = os.getenv('ENVIRONMENT')


def adding_manager_info_for_chats(chats):
    manager_pattern = re.compile(r'^([А-ЯЁ][а-яё]+(?:\s[А-ЯЁ][а-яё]+){1,2}):\s*\n')

    for chat in chats:
        chat['manager_name'] = None
        for message in chat.get('messages'):
            if message.get("direction") == 'out':
                text_content = message.get("content", {}).get("text", "")
                match = manager_pattern.match(text_content)
                if match:
                    manager_name = match.group(1)
                    chat['manager_name'] = manager_name
                    break
    sorted_chats = sorted(chats, key=lambda x: (x['manager_name'] is None, x['manager_name']))
    return sorted_chats


def filter_chats_only_with_text(chats):
    filtered_chats = []
    for chat in chats:
        if chat.get("messages")[0].get("direction") == 'out':  # Skip all chats initialized from Manager
            continue
        if any(message.get("type") == "text" for message in chat.get("messages", [])):
            filtered_chats.append(chat)
    return filtered_chats


async def schedule_filter_chats(filtered_chats_only_with_text: list, avito_account: AvitoAccount):
    filtered_chats = []
    schedule = await sync_to_async(WorkSchedule.objects.filter(avito_account_id=avito_account.id).last)()
    if schedule is None:
        schedule = await sync_to_async(WorkSchedule.objects.filter(id=1).last)()

    for chat in filtered_chats_only_with_text:
        timestamp = chat.get('created')
        # Московский часовой пояс
        moscow_tz = pytz.timezone('Europe/Moscow')

        # Преобразование timestamp в datetime с учётом московского часового пояса
        dt_object = datetime.fromtimestamp(timestamp, tz=moscow_tz)

        # Предположим, у нас есть объект расписания, который мы получили из базы данных
        work_schedule = schedule

        # Определяем день недели (0 - Понедельник, 6 - Воскресенье)
        weekday = dt_object.weekday()

        # Проверяем рабочие часы в зависимости от дня недели
        if weekday < 5:  # Понедельник-Пятница
            start_time = work_schedule.weekday_start
            end_time = work_schedule.weekday_end
        elif weekday == 5:  # Суббота
            if work_schedule.saturday_is_day_off:
                print("Суббота - выходной.")
                continue
            else:
                start_time = work_schedule.saturday_start
                end_time = work_schedule.saturday_end
        elif weekday == 6:  # Воскресенье
            if work_schedule.sunday_is_day_off:
                print("Воскресенье - выходной.")
                continue
            else:
                start_time = work_schedule.sunday_start
                end_time = work_schedule.sunday_end

        # Если день рабочий, сравниваем время
        if 'start_time' in locals() and 'end_time' in locals():
            # Преобразуем время начала и окончания работы в объекты datetime с учётом часового пояса
            start_dt = moscow_tz.localize(datetime.combine(dt_object.date(), start_time))
            end_dt = moscow_tz.localize(datetime.combine(dt_object.date(), end_time))

            if start_dt <= dt_object <= end_dt:
                print(f"Время в рамках рабочего времени.{dt_object.time(), dt_object.weekday()}")
                filtered_chats.append(chat)
            else:
                print(f"Время вне рабочего времени.{dt_object.time(), dt_object.weekday()}")

    return filtered_chats


def get_tokens_information(analyze_by_criteria_raw_result: list):
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


async def get_messaging_week_report_pdf(avito_accounts_id, test_from_prod: bool):
    avito_account = await sync_to_async(AvitoAccount.objects.filter(id=avito_accounts_id).last)()
    if avito_account:
        try:
            chats = await get_chats(avito_account)

            analyze_all_chats = {
                "avito_account_name": avito_account.name,
                "avito_account_id": avito_account.id,
            }
            if chats:
                # Chats actual filtered getting
                actual_chats = await get_chats_for_last_week(chats)
                actual_chats_with_mes = await get_chats_messages(avito_account, actual_chats)

                if len(actual_chats_with_mes) < 2:
                    return False
                else:
                    analyze_all_chats["chats_count"] = len(actual_chats_with_mes)

                #  Separated by managers statistics
                comp_mes_with_man = adding_manager_info_for_chats(actual_chats_with_mes)
                fil_chats_only_with_text = filter_chats_only_with_text(comp_mes_with_man)
                # fil_chats_by_sched = fil_chats_only_with_text
                fil_chats_by_sched = await schedule_filter_chats(fil_chats_only_with_text, avito_account)

                # Checking count of messages for analytics
                if ENVIRONMENT == 'DEVELOPMENT' or test_from_prod:
                    fil_chats_by_sched = fil_chats_by_sched[:10]  # For testing 5items for economy
                else:
                    fil_chats_by_sched = fil_chats_by_sched[:15]

                #  Total statistics
                statistics_total = await get_statistics_total(fil_chats_by_sched)
                if statistics_total:
                    analyze_all_chats["header_with_statistics"] = statistics_total

                stat_split_by_man = await get_stat_total_split_by_man(fil_chats_by_sched)

                if stat_split_by_man:
                    analyze_all_chats["statistics_splitted_by_managers"] = stat_split_by_man
                analyze_messaging = await messaging_total_analyze(fil_chats_by_sched,
                                                                  test_from_prod,
                                                                  avito_account)
                if analyze_messaging:
                    analyze_all_chats["chats"] = analyze_messaging

                analyze_by_crit_raw_res = await analyze_by_criteria(fil_chats_by_sched, test_from_prod,
                                                                    avito_account)
                if analyze_by_crit_raw_res:
                    analyze_by_crit_split_by_man = await get_stat_by_crit_split_by_man(fil_chats_by_sched)
                    analyze_all_chats["analyze_by_criteria"] = analyze_by_crit_split_by_man
        except Exception as send_error:
            sentry_sdk.capture_exception(send_error)
            print(send_error)
            # raise send_error
            return False
        else:
            analyze_all_chats["compared_messages"] = "Чаты не найдены"

        # tokens counting
        if analyze_by_crit_raw_res:
            get_tokens_information(analyze_by_crit_raw_res)

        #TODO PDF CREATING
        if ENVIRONMENT == 'DEVELOPMENT':
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
        pdf_path = reports_dir / f"bad_mes_report_{current_date}_{avito_accounts_id}.pdf"
        pdfkit.from_string(html_content, pdf_path, configuration=config)
        return pdf_path

    else:
        raise HTTPException(status_code=404, detail="error: Аккаунт Avito не найден")


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
                           chats_count=analyze_all_chats['chats_count'],
                           chats=analyze_all_chats.get('chats', []),
                           statistics_total=analyze_all_chats.get("header_with_statistics"),
                           statistics_by_managers=analyze_all_chats.get("statistics_splitted_by_managers"),
                           analyze_by_criteria=analyze_all_chats.get("analyze_by_criteria"),
                           )
