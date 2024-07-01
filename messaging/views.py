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
            size: A4; /* Change from the default size of A4 */
            margin: 0; /* Set margin on each page */
        }
        html,
        body {
            font: normal 14px Montserrat, sans-serif;
            position: relative;
            line-height: normal;
            min-height: 100%;
            width: 100%;
            background: #FFF;
            margin: 0; }
        .d-flex {
            display: -webkit-box;
            display: -ms-flexbox;
            display: flex;
        }
        .flex-wrap {
            -ms-flex-wrap: wrap;
            flex-wrap: wrap;
        }
        .flex-column {
            -webkit-box-orient: vertical;
            -webkit-box-direction: normal;
            -ms-flex-direction: column;
            flex-direction: column;
        }
        .justify-between {
            -webkit-box-pack: justify;
            -ms-flex-pack: justify;
            justify-content: space-between;
        }
        .items-center {
            -webkit-box-align: center;
            -ms-flex-align: center;
            align-items: center;
        }
        * {
            box-sizing: border-box; }
        .page {
            width: 700px;
            margin: 0 auto;}
        .page__top {
            margin-top: 20px;
            width: 100%;
            margin-bottom: 20px;
            -webkit-box-pack: justify;
            -ms-flex-pack: justify;
            justify-content: space-between; }
        .page__top-title {
            color: #20232B;
            font-size: 30px;
            font-weight: 500;
            line-height: 120%; }
        .page__top-text {
            color: #009AD8;
            font-size: 16px;
            font-weight: 400;
            line-height: 100%;
            margin-right: 50px; }
        .page__info {
            width: 100%;
            -webkit-box-pack: justify;
            -ms-flex-pack: justify;
            justify-content: space-between;
            padding-bottom: 10px;
            border-bottom: 1px solid #D9DDE9;}
        .page__info-details {
            flex-grow: 1;
        }
        .page__info .details-column {
            padding-right: 15px;
            min-width: 50%;
            }
        .page__info .details-column__info {
            padding-left: 5px; }
        .page__info .details-column__info-title {
            color: #A3A3A3;
            font-size: 10px;
            font-weight: 500;
            line-height: 100%;
            margin-bottom: 3px;
            white-space: nowrap; }
        .page__info .details-column__info-value {
            color: #20232B;
            font-size: 14px;
            font-weight: 500;
            line-height: 120%;
            white-space: normal;
            word-break: break-word}
        .page__info-logo {
            margin-left: auto;
            display: flex;
            width: 180px;
            min-width: 180px;
            align-items: center;}
        .page__info-logo svg {
            margin-left: 12px;
        }
        .chats {
            width: 100%;
        }
        .chat {
            width: 100%;
            margin-top: 20px;
            border-radius: 20px;
            border: 1px solid #E4EDF1;
            padding: 10px;
        }
        .chat__info {
            color: #20232B;
            font-size: 16px;
            font-weight: 500;
            letter-spacing: -.4px;
            margin-bottom: 20px;
        }
        .chat__info-link {
            color: #009AD8;
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -.4px;
        }
        .chat__item {
            width: 100%;
            margin-bottom: 10px;
            padding: 5px;
            border-radius: 5px;
        }
        .chat__item--client {
            background-color: #F3F5F8;
        }
        .chat__item-author {
            color: #20232B;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: -.4px;
        }
        .chat__item-message {
            color: #20232B;
            font-size: 14px;
            font-weight: 400;
            letter-spacing: -.4px;
        }
        .chat__analysis {
            width: 100%;
            font-size: 14px;
            color: #20232B;
            background-color: #F3F5F8;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        .chat__analysis b {
            width: 100%;
            display: block;
            margin-bottom: 5px;
        }
    </style>
    </head>
    <body>
<div class="page">
    <div class="page__top d-flex items-center">
        <span class="page__top-title">Аналитика переписок аккаунта</span>
        <span class="page__top-text">Сервис <br>аналитики <br>Авито</span>
    </div>

    <div class="page__info d-flex items-center">
        <div class="page__info-details d-flex">
            <div class="details-column d-flex items-end"> 
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <g id="vuesax/linear/monitor-mobbile">
                        <g id="monitor-mobbile">
                            <path id="Vector" d="M10 16.95H6.21C2.84 16.95 2 16.11 2 12.74V6.74003C2 3.37003 2.84 2.53003 6.21 2.53003H16.74C20.11 2.53003 20.95 3.37003 20.95 6.74003" stroke="#009AD8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                            <path id="Vector_2" d="M10 21.47V16.95" stroke="#009AD8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                            <path id="Vector_3" d="M2 12.95H10" stroke="#009AD8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                            <path id="Vector_4" d="M6.73999 21.47H9.99999" stroke="#009AD8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                            <path id="Vector_5" d="M22 12.8V18.51C22 20.88 21.41 21.47 19.04 21.47H15.49C13.12 21.47 12.53 20.88 12.53 18.51V12.8C12.53 10.43 13.12 9.84003 15.49 9.84003H19.04C21.41 9.84003 22 10.43 22 12.8Z" stroke="#009AD8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                            <path id="Vector_6" d="M17.2445 18.25H17.2535" stroke="#009AD8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </g>
                    </g>
                </svg>
                <div class="details-column__info d-flex flex-column">
                    <span class="details-column__info-title">Аккаунт</span>
                    <span class="details-column__info-value">{{ avito_account_name }}</span>
                </div>
            </div>

            <div class="details-column d-flex items-end" style="min-width: auto;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M8 2V5" stroke="#009AD8" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M16 2V5" stroke="#009AD8" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M3.5 9.08997H20.5" stroke="#009AD8" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M21 8.5V17C21 20 19.5 22 16 22H8C4.5 22 3 20 3 17V8.5C3 5.5 4.5 3.5 8 3.5H16C19.5 3.5 21 5.5 21 8.5Z" stroke="#009AD8" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M11.9955 13.7H12.0045" stroke="#009AD8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M8.29431 13.7H8.30329" stroke="#009AD8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M8.29431 16.7H8.30329" stroke="#009AD8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <div class="details-column__info d-flex flex-column">
                    <span class="details-column__info-title">Период</span>
                    <span class="details-column__info-value" style="white-space: nowrap; margin-right: 30px">{{ start_date }} - {{ end_date }}</span>
                </div>
            </div>
        </div>

        <div class="page__info-logo">
            <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="200px" height="51px" viewBox="0 0 200 51" version="1.1">
                <g id="surface1">
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(0%,0%,0%);fill-opacity:1;" d="M 76.449219 1.199219 L 59.195312 46.394531 L 68.46875 46.394531 L 72.050781 36.957031 L 90.367188 36.957031 L 93.933594 46.394531 L 103.136719 46.394531 L 85.945312 1.199219 Z M 75.191406 28.660156 L 81.226562 12.757812 L 87.230469 28.660156 Z M 75.191406 28.660156 "/>
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(0%,0%,0%);fill-opacity:1;" d="M 183.589844 14.074219 C 180.34375 14.074219 177.171875 15.039062 174.476562 16.84375 C 171.777344 18.652344 169.675781 21.21875 168.433594 24.222656 C 167.191406 27.230469 166.867188 30.535156 167.5 33.726562 C 168.132812 36.914062 169.695312 39.84375 171.992188 42.144531 C 174.285156 44.445312 177.207031 46.011719 180.386719 46.644531 C 183.570312 47.28125 186.867188 46.953125 189.867188 45.710938 C 192.863281 44.464844 195.425781 42.359375 197.226562 39.652344 C 199.03125 36.949219 199.992188 33.769531 199.992188 30.515625 C 199.992188 26.15625 198.261719 21.972656 195.1875 18.890625 C 192.109375 15.804688 187.9375 14.074219 183.589844 14.074219 Z M 183.589844 38.53125 C 182.007812 38.53125 180.464844 38.058594 179.148438 37.179688 C 177.835938 36.300781 176.8125 35.046875 176.207031 33.585938 C 175.601562 32.121094 175.441406 30.511719 175.753906 28.957031 C 176.058594 27.402344 176.820312 25.976562 177.9375 24.855469 C 179.054688 23.734375 180.480469 22.972656 182.03125 22.664062 C 183.578125 22.351562 185.1875 22.511719 186.648438 23.117188 C 188.105469 23.726562 189.355469 24.75 190.234375 26.070312 C 191.109375 27.386719 191.578125 28.933594 191.578125 30.519531 C 191.582031 31.570312 191.375 32.613281 190.972656 33.585938 C 190.574219 34.558594 189.984375 35.445312 189.242188 36.1875 C 188.5 36.933594 187.617188 37.523438 186.648438 37.925781 C 185.679688 38.324219 184.636719 38.53125 183.589844 38.53125 Z M 183.589844 38.53125 "/>
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(0%,0%,0%);fill-opacity:1;" d="M 114.183594 34.738281 L 106.695312 14.644531 L 97.851562 14.644531 L 109.90625 46.394531 L 118.679688 46.394531 L 130.519531 14.644531 L 121.675781 14.644531 Z M 114.183594 34.738281 "/>
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(0%,0%,0%);fill-opacity:1;" d="M 158.335938 6.207031 L 149.921875 6.207031 L 149.921875 14.644531 L 145 14.644531 L 145 22.222656 L 149.921875 22.222656 L 149.921875 35.742188 C 149.921875 43.394531 154.128906 46.683594 160.050781 46.683594 C 162.058594 46.710938 164.050781 46.320312 165.898438 45.539062 L 165.898438 37.671875 C 164.894531 38.042969 163.832031 38.242188 162.757812 38.253906 C 160.203125 38.253906 158.335938 37.253906 158.335938 33.820312 L 158.335938 22.222656 L 165.898438 22.222656 L 165.898438 14.644531 L 158.335938 14.644531 Z M 158.335938 6.207031 "/>
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(0%,0%,0%);fill-opacity:1;" d="M 137.4375 12.355469 C 140.824219 12.355469 143.574219 9.601562 143.574219 6.207031 C 143.574219 2.808594 140.824219 0.0546875 137.4375 0.0546875 C 134.050781 0.0546875 131.300781 2.808594 131.300781 6.207031 C 131.300781 9.601562 134.050781 12.355469 137.4375 12.355469 Z M 137.4375 12.355469 "/>
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(0%,0%,0%);fill-opacity:1;" d="M 141.648438 14.644531 L 133.230469 14.644531 L 133.230469 46.394531 L 141.648438 46.394531 Z M 141.648438 14.644531 "/>
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(1.568627%,87.843137%,38.039216%);fill-opacity:1;" d="M 16.460938 50.902344 C 25.523438 50.902344 32.867188 43.539062 32.867188 34.453125 C 32.867188 25.367188 25.523438 18.003906 16.460938 18.003906 C 7.398438 18.003906 0.0546875 25.367188 0.0546875 34.453125 C 0.0546875 43.539062 7.398438 50.902344 16.460938 50.902344 Z M 16.460938 50.902344 "/>
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(100%,25.098039%,32.54902%);fill-opacity:1;" d="M 44.921875 48.828125 C 50.398438 48.828125 54.835938 44.375 54.835938 38.886719 C 54.835938 33.398438 50.398438 28.949219 44.921875 28.949219 C 39.449219 28.949219 35.007812 33.398438 35.007812 38.886719 C 35.007812 44.375 39.449219 48.828125 44.921875 48.828125 Z M 44.921875 48.828125 "/>
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(58.823529%,36.862745%,92.156863%);fill-opacity:1;" d="M 19.597656 15.859375 C 22.988281 15.859375 25.734375 13.105469 25.734375 9.710938 C 25.734375 6.3125 22.988281 3.558594 19.597656 3.558594 C 16.210938 3.558594 13.464844 6.3125 13.464844 9.710938 C 13.464844 13.105469 16.210938 15.859375 19.597656 15.859375 Z M 19.597656 15.859375 "/>
                    <path style=" stroke:none;fill-rule:nonzero;fill:rgb(0%,66.666667%,100%);fill-opacity:1;" d="M 41.070312 26.800781 C 48.4375 26.800781 54.410156 20.8125 54.410156 13.429688 C 54.410156 6.042969 48.4375 0.0546875 41.070312 0.0546875 C 33.703125 0.0546875 27.730469 6.042969 27.730469 13.429688 C 27.730469 20.8125 33.703125 26.800781 41.070312 26.800781 Z M 41.070312 26.800781 "/>
                </g>
            </svg>
        </div>
    </div>

    <div class="chats">
        {% for chat in data %}
            <div class="chat">
                <div class="chat__info">
                    Ссылка на чат (неоходима авторизация на Авито): <a href="https://www.avito.ru/profile/messenger/channel/{{ chat.chat_id }}" class="chat__info-link" target="_blank">Перейти в чат</a>
                </div>
                {% for message in chat.chat_text %}
                    {% if message.role == 'user' %}
                        <div class="chat__item chat__item--client">
                            <span class="chat__item-author">Клиент:</span>
                            <span class="chat__item-message"> {{ message.content }}</span>
                        </div>
                    {% endif %}
    
                    {% if message.role == 'assistant' %}
                    <div class="chat__item">
                        <span class="chat__item-author">Менеджер:</span>
                        <span class="chat__item-message"> {{ message.content }}</span>
                    </div>
                    {% endif %}
                {% endfor %}
    
                <div class="chat__analysis">
                    <b>Анализ переписки:</b>
                    {{ chat.analysis }}
                </div>
            </div>
        {% endfor %}
    </div>
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
