from avito_account.models import AvitoAccount
from exceptions import HTTPException
from messaging.api import get_chats, get_chats_messages
from jinja2 import Template
from weasyprint import HTML
from asgiref.sync import sync_to_async
from pathlib import Path
from datetime import datetime, timedelta

from messaging.bad_mes_report.header.header_utils import get_statistics_total, get_statistics_splitted_by_managers
from messaging.bad_mes_report.utils_open_ai import messaging_total_analyze, analyze_by_criteria
from messaging.views import get_chats_for_last_week
import re


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
        if any(message.get("type") == "text" for message in chat.get("messages", [])):
            filtered_chats.append(chat)
    return filtered_chats


async def get_messaging_week_report_pdf(avito_accounts_id):
    analyze_all_chats = []
    avito_account = await sync_to_async(AvitoAccount.objects.filter(id=avito_accounts_id).last)()
    if avito_account:
        chats = await get_chats(avito_account)
        analyze_all_chats.append({
            "avito_account_name": avito_account.name,
            "avito_account_id": avito_account.id,
        })
        if chats:
            actual_chats = await get_chats_for_last_week(chats)
            actual_chats_with_messages = await get_chats_messages(avito_account, actual_chats)
            if len(actual_chats_with_messages) < 2:
                return False
            else:
                analyze_all_chats[-1]["chats_count"] = len(actual_chats_with_messages)
            #  Total statistics
            statistics_total = await get_statistics_total(actual_chats_with_messages=actual_chats_with_messages)
            if statistics_total:
                analyze_all_chats[-1]["header_with_statistics"] = statistics_total

            #  Separated by managers statistics
            compared_messages_with_manager = adding_manager_info_for_chats(actual_chats_with_messages)
            statistics_splitted_by_managers = await get_statistics_splitted_by_managers(
                actual_chats_with_messages=compared_messages_with_manager
            )
            if statistics_splitted_by_managers:
                analyze_all_chats[-1]["statistics_splitted_by_managers"] = statistics_splitted_by_managers

            #TODO сделать ИИ анализ analyze_messaging и by_criteria из одной фунции
            filtered_chats_only_with_text = filter_chats_only_with_text(compared_messages_with_manager)

            analyze_messaging = messaging_total_analyze(filtered_chats_only_with_text)
            if analyze_messaging:
                analyze_all_chats[-1]["chats"] = analyze_messaging

            # analyze_by_criteria_result = await analyze_by_criteria(filtered_chats_only_with_text, avito_account)
            # if analyze_by_criteria:
            #     analyze_all_chats[-1]["analyze_by_criteria"] = analyze_by_criteria_result
        else:
            analyze_all_chats[-1]["compared_messages"] = "Чаты не найдены"

        #TODO PDF CREATING
        html_content = await bad_messaging_report_generate_html(analyze_all_chats=analyze_all_chats)
        pdf_file = HTML(string=html_content).write_pdf()
        # Get the current date in dd.mm.yyyy format
        current_date = datetime.now().strftime("%d.%m.%Y")
        # Define the directory and file path with the date
        reports_dir = Path("messaging/bad_mes_report/PDFs")
        reports_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = reports_dir / f"bad_mes_report_{current_date}_{avito_accounts_id}.pdf"
        # Save the PDF file
        with open(pdf_path, "wb") as f:
            f.write(pdf_file)
        # Return the absolute path to the saved PDF
        return str(pdf_path.resolve())

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
    avito_account_name = analyze_all_chats[0]['avito_account_name'] if analyze_all_chats else "Неизвестно"

    # Генерация HTML с использованием шаблона и данных
    return template.render(avito_account_name=avito_account_name,
                           start_date=start_date,
                           end_date=end_date,
                           chats_count=analyze_all_chats[0]['chats_count'],
                           chats=analyze_all_chats[0].get('chats', []),
                           statistics_total=analyze_all_chats[0].get("header_with_statistics"),
                           statistics_by_managers=analyze_all_chats[0].get("statistics_splitted_by_managers"),
                           )
