import datetime
from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views import View
from avito_account.models import AvitoAccount
from messaging.api import get_chats, get_chats_messages
from messaging.utils_duration import get_answer_durations
from messaging.utils_open_ai import compare_messages_for_ai, analyze_overall_conversation


async def get_chats_for_last_week(chats: list) -> list:
    filtered_chats = []
    now = datetime.datetime.now()

    if len(chats) > 0:
        for chat in chats:
            updated = datetime.datetime.fromtimestamp(chat.get("updated"))
            timedelta = now - updated
            print(timedelta)
            if 7 >= timedelta.days > -1:
                filtered_chats.append(chat)
        return filtered_chats


async def convert_seconds(seconds):
    td = datetime.timedelta(seconds=seconds)
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} д")
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes} м")
    if seconds > 0:
        parts.append(f"{seconds} с")

    return ": ".join(parts)


async def get_duration_statistics(chats: list):
    statistics = {}
    total_sum = sum([chat[0] for chat in chats])
    total_len = len(chats)
    if total_sum > 0 and total_len > 0:
        average_duration = total_sum / total_len
        average_duration_formatted = await convert_seconds(average_duration)
        statistics["average_duration"] = average_duration_formatted

    top_durations = sorted(chats, key=lambda x: x[0])[::-1][:10]
    top_durations_formatted = [[await convert_seconds(duration[0]), duration[1], duration[2]] for duration in
                               top_durations]
    statistics["top_durations"] = top_durations_formatted
    return statistics


class DurationWeekStatisticsView(View):
    async def get(self, request, *args, **kwargs):
        telegram_id = kwargs.get("telegram_id", None)
        avito_account = await sync_to_async(AvitoAccount.objects.filter(telegram_id=telegram_id).last)()

        if avito_account:
            chats = await get_chats(avito_account)
            if chats:
                actual_chats = await get_chats_for_last_week(chats)
                actual_chats_with_messages = await get_chats_messages(avito_account, actual_chats)
                durations = await get_answer_durations(actual_chats_with_messages)
                duration_statistics = await get_duration_statistics(durations)
                return JsonResponse(duration_statistics, safe=False)
            else:
                return JsonResponse(status=404, data={"error": "Чаты не найдены"})
        else:
            return JsonResponse(status=404, data={"error": "Аккаунт Avito не найден"})


from django.http import JsonResponse, HttpResponse
from django.views import View
from jinja2 import Template
from weasyprint import HTML
from asgiref.sync import sync_to_async



class BadMessagingWeekReportView(View):
    async def get(self, request, *args, **kwargs):
        analyze_all_chats = []
        avito_accounts_id = kwargs.get("avito_accounts_id", None)
        avito_account = await sync_to_async(AvitoAccount.objects.filter(id=avito_accounts_id).last)()
        if avito_account:
            chats = await get_chats(avito_account)
            # ADD RESULTS
            analyze_all_chats.append({
                "avito_account_name": avito_account.name,
                "avito_account_id": avito_account.id,
            })
            if chats:  # 5 lines down duplicated from DurationWeekStatisticsView
                actual_chats = await get_chats_for_last_week(chats)
                actual_chats_with_messages = await get_chats_messages(avito_account, actual_chats)
                compared_messages = compare_messages_for_ai(actual_chats_with_messages)
                analyze = analyze_overall_conversation(compared_messages)
                if analyze:
                    analyze_all_chats[-1]["analyze"] = analyze
            else:
                analyze_all_chats[-1]["compared_messages"] = "Чаты не найдены 404"

            # Преобразование данных в HTML и PDF
            html_content = self.generate_html(analyze_all_chats)
            pdf_file = HTML(string=html_content).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="chat_analysis_report.pdf"'
            return response
        else:
            return JsonResponse(status=404, data={"error": "Аккаунт Avito не найден"})

    def generate_html(self, data):
        template = Template('''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">
        <title>Аналитика авито аккаунта</title>
        <link href="https://fonts.googleapis.com/css?family=Montserrat:100,100i,200,200i,300,300i,400,400i,500,500i,600,600i,700,700i,800,800i,900,900i&display=swap&subset=cyrillic,cyrillic-ext,latin-ext" rel="stylesheet">
        <style>
            @page {
                size: A4;
                margin: 0;
            }
            html,
            body {
                font: normal 14px Montserrat, sans-serif;
                position: relative;
                line-height: normal;
                min-height: 100%;
                width: 100%;
                background: #FFF;
                margin: 0;
            }
            .container {
                width: 800px;
                margin: 20px auto;
            }
            .header {
                text-align: center;
                margin-bottom: 20px;
            }
            .header h1 {
                font-size: 28px;
                font-weight: 700;
                color: #20232B;
            }
            .header h2 {
                font-size: 16px;
                font-weight: 400;
                color: #99A3B1;
            }
            .report {
                border: 1px solid #E4EDF1;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .report .chat-link {
                font-size: 14px;
                color: #009AD8;
                margin-bottom: 10px;
            }
            .report .chat-text {
                font-size: 14px;
                color: #20232B;
                white-space: pre-line;
                margin-bottom: 10px;
            }
            .report .analysis {
                font-size: 14px;
                color: #20232B;
                background-color: #F3F5F8;
                padding: 10px;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Аналитика авито аккаунта - {{ avito_account_name }}</h1>
                <h2>за период с {{ start_date }} по {{ end_date }}</h2>
            </div>

            {% for chat in data %}
            <div class="report">
                <div class="chat-link">
                    Ссылка на чат: <a href="https://www.avito.ru/profile/messenger/channel/u2i-FLEHg_5TEmFxC9uhQlqklg/{{ chat.chat_id }}">перейти в чат</a>
                </div>
                <div class="chat-text">
                    {% for message in chat.chat_text %}
                        <strong>{{ message.role|replace('user', 'Клиент')|replace('assistant', 'Менеджер') }}:</strong> {{ message.content }}<br>
                    {% endfor %}
                </div>
                <div class="analysis">
                    <strong>Анализ переписки:</strong> {{ chat.analysis }}
                </div>
            </div>
            {% endfor %}

        </div>
    </body>
    </html>
        ''')

        # Примерные данные для периода (можно обновить по требованию)
        start_date = "01.01.2024"
        end_date = "07.01.2024"
        avito_account_name = data[0]['avito_account_name'] if data else "Неизвестно"

        return template.render(data=data[0].get('analyze', []), avito_account_name=avito_account_name,
                               start_date=start_date, end_date=end_date)


