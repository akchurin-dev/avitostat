from avito_account.models import AvitoAccount
from exceptions import HTTPException
from messaging.api import get_chats, get_chats_messages
from jinja2 import Template
from weasyprint import HTML
from asgiref.sync import sync_to_async
from pathlib import Path
from datetime import datetime

from messaging.bad_mes_report.header.header_utils import get_statistics_total, get_statistics_splitted_by_managers
from messaging.bad_mes_report.utils_open_ai import compare_messages_for_ai, messaging_total_analyze, analyze_by_criteria
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
            #  Total statistics
            statistics_total = await get_statistics_total(
                actual_chats_with_messages=actual_chats_with_messages)
            if statistics_total:
                analyze_all_chats[-1]["header_with_statistics"] = statistics_total

            #  Separated by managers statistics
            compared_messages_with_manager = adding_manager_info_for_chats(actual_chats_with_messages)
            statistics_splitted_by_managers = await get_statistics_splitted_by_managers(
                actual_chats_with_messages=compared_messages_with_manager
            )
            compared_messages = compare_messages_for_ai(actual_chats_with_messages)  # We need AI analyze NOT separated by manager



            #TODO сделать ИИ анализ analyze_messaging и by_criteria из одной фунции
            analyze_messaging = messaging_total_analyze(compared_messages_with_manager)
            if analyze_messaging:
                analyze_all_chats[-1]["analyze"] = analyze_messaging
            by_criteria = await analyze_by_criteria(compared_messages_with_manager, avito_account)
            if by_criteria:
                analyze_all_chats[-1]["analyze_by_criteria"] = analyze_messaging
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
    from datetime import datetime, timedelta
    template = Template('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Main page</title>
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
        .justify-center {
            -webkit-box-pack: center;
            -ms-flex-pack: center;
            justify-content: center;
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
        .items-end {
            -webkit-box-align: end;
            -ms-flex-align: end;
            align-items: end;
        }
        * {
            box-sizing: border-box; }
        .page {
            width: 750px;
            margin: 0 auto;}
        .page__top {
            margin-top: 20px;
            width: 100%;
            margin-bottom: 30px;}
        .page__top-title {
            height: 70px;
            border-radius: 0 35px 35px 0;
            border: 1px solid #00D8BF;
            color: #20232B;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -.76px;
            padding-right: 20px;
            border-left: none;}
        .page__top-icon {
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border: 1px solid #00D8BF;
            margin-left: 5px;
        }
        .page__info {
            width: 100%;
            padding-bottom: 35px;}
        .page__info-items {
            width: 600px;}
        .page__info-item {
            height: 30px;
            border-radius: 15px;
            border: 1px solid #00D8BF;
            padding: 0 10px;
            color: #20232B;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: -.4px;
            white-space: nowrap;
        }
        .page__info-item:first-child {
            background-color: #00D8BF;
            color:#FFF;}
        .page__info-item span {
            white-space: nowrap;
            float: left;
        }
        .page__info-item span:last-child {
            color: #00D8BF;
            margin-left: 3px;
        }
        .page__info-logo {
            width: 158px;
            margin-top: -108px;
        }
        .page__info-logo svg {
            margin-left: 10px;
            width: 148px;
        }
        .page .page__title {
            display: block;
            width: 100%;
            color: #20232B;
            font-size: 20px;
            font-weight: 700;
            line-height: 100%;
            letter-spacing: -.4px;
            border-bottom: 1px solid #00D8BF;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .page .reports {
            width: 100%;
            margin-bottom: 40px;
            float: left;
        }
        .page .reports__top {
            width: 100%;
            padding: 0 10px;
        }
        .page .reports__top-manager {
            color: #20232B;
            font-size: 14px;
            font-weight: 700;
            line-height: 100%;
            margin-right: 10px;
        }
        .page .reports__top svg {
            margin-right: 5px;
        }
        .page .reports .report {
            float: left;
            width: 50%;
            margin-top: 15px;
        }
        .page .reports .report__inner {
            width: 100%;
            min-height: 40px;
            border-radius: 14px;
            background-color: #F3F5F8;
            padding: 5px 5px 5px 10px;
        }
        .page .reports .report:nth-child(odd) {
            padding-left: 5px;
        }
        .page .reports .report:nth-child(even) {
            padding-right: 5px;
        }
        .page .reports .report__title {
            flex-grow: 1;
            color: #20232B;
            font-size: 12px;
            font-weight: 500;
            line-height: 100%;
            padding-right: 10px;
        }
        .page .reports .report__info {
            height: 30px;
            border-radius: 10px;
            background-color: #FFF;
            color: #20232B;
            font-size: 18px;
            font-weight: 500;
            letter-spacing: -.8px;
            padding: 5px 5px 5px 10px;
            min-width: 150px;
        }
        .page .reports .report__info-status {
            height: 16px;
            border-radius: 4px;
            padding: 0 5px;
            color: #FFF;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            margin-left: 10px;
        }
        .page .parameters {
            width: 100%;
            margin-bottom: 20px;
            float: left;
        }
        .page .parameters__item {
            width: 50%;
            float: left;
            margin-bottom: 10px;
            font-size: 12px;
            font-weight: 400;
            line-height: 12px;
            letter-spacing: -.02em;
            color: #000;
        }
        .page .parameters__item-inner {
            width: 100%;
        }
        .page .parameters__item:nth-child(odd) {
            padding-right: 5px;
        }
        .page .parameters__item:nth-child(even) {
            padding-left: 5px;
        }
        .page .parameters__item-status {
            width: 25px;
            min-width: 25px;
            height: 15px;
            border-radius: 4px;
            margin: 0 5px;
        }
        .page .tips {
            float: left;
            width: 100%;
            margin-bottom: 30px;
        }
        .page .tips__item {
            width: 50%;
        }
        .page .tips__item-column {
            height: 100%;
            padding: 10px 30px;
            border-radius: 60px;
            border: 1px solid #00D8BF;
            width: 300px;
            font-size: 12px;
            font-weight: 400;
            line-height: 12px;
            letter-spacing: -.02em;
            text-align: center;
        }
        .page .manager {
            width: 100%;
        }
        .page .manager__title {
            width: 100%;
            margin-bottom: 15px;
            font-size: 14px;
            font-weight: 700;
            line-height: 14px;
            color: #20232B;
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
        .chat__manager {
            display: inline-block;
            color: #009AD8;
            font-size: 14px;
            font-weight: 700;
            line-height: 100%;
            margin-bottom: 10px;
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
        <span class="page__top-title d-flex items-center">Обзорный отчет по перепискам</span>
        <div class="page__top-icon d-flex items-center justify-center">
            <svg width="33" height="32" viewBox="0 0 33 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M0.999996 16.1943C0.997044 18.156 1.39377 20.099 2.16742 21.9118C2.94107 23.7245 4.07642 25.3714 5.50833 26.758C6.9407 28.1463 8.64134 29.2475 10.5131 29.9986C12.3848 30.7497 14.3909 31.1359 16.4167 31.1352C18.5971 31.1405 20.7535 30.6944 22.7417 29.8269L29.1867 30.7508C29.5067 30.8015 29.8346 30.7756 30.1419 30.6755C30.4493 30.5755 30.7268 30.4042 30.9503 30.1766C31.1739 29.9489 31.3367 29.6719 31.4246 29.3694C31.5126 29.067 31.523 28.7483 31.455 28.441L30.56 22.1045C31.4093 20.2433 31.8432 18.2293 31.8333 16.1943C31.8361 14.2327 31.4393 12.2897 30.6657 10.477C29.892 8.66426 28.7568 7.01735 27.325 5.6307C25.8927 4.24228 24.1921 3.14104 22.3203 2.38996C20.4486 1.63888 18.4425 1.25267 16.4167 1.25342C12.3256 1.25368 8.40209 2.82812 5.50833 5.6307C4.07716 7.01778 2.94229 8.66477 2.1687 10.4774C1.3951 12.2901 0.997954 14.2328 0.999996 16.1943Z" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M16.4167 17.1797C16.1469 17.1797 15.888 17.0758 15.6972 16.8909C15.5064 16.706 15.3992 16.4552 15.3992 16.1936C15.3992 15.9321 15.5064 15.6813 15.6972 15.4963C15.888 15.3114 16.1469 15.2075 16.4167 15.2075C16.6866 15.2075 16.9454 15.3114 17.1362 15.4963C17.327 15.6813 17.4342 15.9321 17.4342 16.1936C17.4342 16.4552 17.327 16.706 17.1362 16.8909C16.9454 17.0758 16.6866 17.1797 16.4167 17.1797ZM9.28504 17.1797C9.01518 17.1797 8.75638 17.0758 8.56556 16.8909C8.37474 16.706 8.26754 16.4552 8.26754 16.1936C8.26754 15.9321 8.37474 15.6813 8.56556 15.4963C8.75638 15.3114 9.01518 15.2075 9.28504 15.2075C9.5549 15.2075 9.8137 15.3114 10.0045 15.4963C10.1953 15.6813 10.3025 15.9321 10.3025 16.1936C10.3025 16.4552 10.1953 16.706 10.0045 16.8909C9.8137 17.0758 9.5549 17.1797 9.28504 17.1797ZM23.5484 17.1797C23.4148 17.1798 23.2824 17.1544 23.1589 17.105C23.0354 17.0555 22.9232 16.983 22.8287 16.8915C22.7341 16.8 22.659 16.6913 22.6078 16.5717C22.5566 16.4521 22.5302 16.3239 22.53 16.1944C22.5299 16.0649 22.5561 15.9367 22.6072 15.817C22.6582 15.6973 22.7331 15.5886 22.8275 15.4969C22.9219 15.4053 23.034 15.3325 23.1574 15.2829C23.2808 15.2332 23.4131 15.2076 23.5467 15.2075C23.8166 15.2075 24.0754 15.3114 24.2662 15.4963C24.457 15.6813 24.5642 15.9321 24.5642 16.1936C24.5642 16.4552 24.457 16.706 24.2662 16.8909C24.0754 17.0758 23.8182 17.1797 23.5484 17.1797Z" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
    </div>

    <div class="page__info d-flex items-end">
        <div class="page__info-items d-flex">
            <div class="page__info-item d-flex items-center">Моя Стройка</div>
            <div class="page__info-item d-flex items-center">Период с 19.05 по 27.05</div>
            <div class="page__info-item" style="line-height: 30px"><span>Количество обращений:&nbsp;</span><span>20</span></div>
        </div>

        <div class="page__info-logo">
            <img src="images/avitostata.svg" alt="logo">
            <!--<svg width="148" height="138" viewBox="0 0 148 138" fill="none" xmlns="http://www.w3.org/2000/svg">
                <ellipse cx="73.6719" cy="48.9282" rx="48.4977" ry="48.9282" fill="url(#paint0_linear_17_32)"/>
                <mask id="mask0_17_32" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="24" y="0" width="98" height="98">
                    <ellipse cx="73.385" cy="48.9282" rx="48.4977" ry="48.9282" fill="url(#paint1_linear_17_32)"/>
                </mask>
                <g mask="url(#mask0_17_32)">
                    <ellipse cx="100.647" cy="48.9282" rx="48.4977" ry="48.9282" fill="url(#paint2_linear_17_32)"/>
                </g>
                <ellipse cx="73.5" cy="72" rx="24.5" ry="21" fill="url(#paint3_linear_17_32)"/>
                <ellipse cx="73.5286" cy="28.1229" rx="25.3967" ry="23.2445" fill="url(#paint4_linear_17_32)"/>
                <ellipse cx="51.5754" cy="50.2196" rx="23.5314" ry="24.6793" fill="#1E3158"/>
                <ellipse cx="95.1945" cy="50.5065" rx="23.5314" ry="24.6793" fill="url(#paint5_linear_17_32)"/>
                <mask id="mask1_17_32" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="48" y="4" width="51" height="48">
                    <ellipse cx="73.5286" cy="28.1229" rx="25.3967" ry="23.2445" fill="#0ABEF2"/>
                </mask>
                <g mask="url(#mask1_17_32)">
                    <ellipse cx="51.5754" cy="50.2196" rx="23.5314" ry="24.6793" fill="url(#paint6_linear_17_32)"/>
                    <g filter="url(#filter0_d_17_32)">
                        <ellipse cx="94.7685" cy="50.2196" rx="23.5314" ry="24.6793" fill="url(#paint7_linear_17_32)"/>
                    </g>
                </g>
                <mask id="mask2_17_32" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="48" y="47" width="51" height="44">
                    <ellipse cx="73.5286" cy="69.0924" rx="25.3967" ry="21.1444" fill="#F11346"/>
                </mask>
                <g mask="url(#mask2_17_32)">
                    <ellipse cx="51.5314" cy="50.6793" rx="23.5314" ry="24.6793" fill="#F61847"/>
                    <ellipse cx="94.1948" cy="50.2193" rx="23.5314" ry="24.6793" fill="url(#paint8_linear_17_32)"/>
                </g>
                <ellipse cx="73.5284" cy="49.3584" rx="5.30892" ry="5.4524" fill="#193250"/>
                <rect x="88.6382" y="106.752" width="16.0702" height="4.30453" rx="2.15226" fill="#1B2F50"/>
                <rect x="40.8447" y="133.44" width="61.4113" height="4.30453" rx="2.15226" fill="url(#paint9_linear_17_32)"/>
                <circle cx="18.1523" cy="135.593" r="2.15226" fill="#14C7EF"/>
                <circle cx="25.3265" cy="135.593" r="2.15226" fill="#14C7EF"/>
                <circle cx="118.152" cy="135.152" r="2.15226" fill="#7ECA05"/>
                <circle cx="125.326" cy="135.152" r="2.15226" fill="#7ECA05"/>
                <path d="M112.856 117.824L110.672 113.336L108.44 117.824H112.856ZM102.248 122.144L103.784 118.976C103.832 118.904 103.856 118.856 103.88 118.784L109.016 108.344C109.352 107.648 109.904 107.312 110.672 107.312C111.44 107.312 111.992 107.648 112.304 108.344L119.072 122.144C119.576 123.152 119.216 124.136 118.256 124.616C117.968 124.76 117.728 124.808 117.44 124.808C116.696 124.808 116.12 124.472 115.784 123.776L114.68 121.52H106.64L105.536 123.776C105.056 124.76 104.072 125.096 103.088 124.616C102.104 124.136 101.744 123.152 102.248 122.144ZM129.29 107.312C130.37 107.312 131.138 108.056 131.138 109.16C131.138 110.24 130.37 111.008 129.29 111.008H126.05V122.96C126.05 124.04 125.282 124.808 124.202 124.808C123.122 124.808 122.354 124.04 122.354 122.96V111.008H119.114C118.034 111.008 117.266 110.24 117.266 109.16C117.266 108.056 118.034 107.312 119.114 107.312H129.29ZM139.95 117.824L137.766 113.336L135.534 117.824H139.95ZM129.342 122.144L130.878 118.976C130.926 118.904 130.95 118.856 130.974 118.784L136.11 108.344C136.446 107.648 136.998 107.312 137.766 107.312C138.534 107.312 139.086 107.648 139.398 108.344L146.166 122.144C146.67 123.152 146.31 124.136 145.35 124.616C145.062 124.76 144.822 124.808 144.534 124.808C143.79 124.808 143.214 124.472 142.878 123.776L141.774 121.52H133.734L132.63 123.776C132.15 124.76 131.166 125.096 130.182 124.616C129.198 124.136 128.838 123.152 129.342 122.144Z" fill="#1B2F50"/>
                <path d="M11.856 117.824L9.672 113.336L7.44 117.824H11.856ZM1.248 122.144L2.784 118.976C2.832 118.904 2.856 118.856 2.88 118.784L8.016 108.344C8.352 107.648 8.904 107.312 9.672 107.312C10.44 107.312 10.992 107.648 11.304 108.344L18.072 122.144C18.576 123.152 18.216 124.136 17.256 124.616C16.968 124.76 16.728 124.808 16.44 124.808C15.696 124.808 15.12 124.472 14.784 123.776L13.68 121.52H5.64L4.536 123.776C4.056 124.76 3.072 125.096 2.088 124.616C1.104 124.136 0.744 123.152 1.248 122.144ZM30.6424 107.48C31.6504 107.888 32.0584 108.872 31.6264 109.88L25.7224 123.68C25.3864 124.4 24.8104 124.808 24.0184 124.808C23.2264 124.808 22.6504 124.4 22.3144 123.68L16.4104 109.88C15.9784 108.872 16.3864 107.888 17.3944 107.48C18.4024 107.024 19.3624 107.408 19.7944 108.416L24.0184 118.304L28.2424 108.416C28.6744 107.408 29.6344 107.024 30.6424 107.48ZM36.1725 107.312C37.2525 107.312 38.0205 108.056 38.0205 109.16V122.96C38.0205 124.04 37.2525 124.808 36.1725 124.808C35.0685 124.808 34.3245 124.04 34.3245 122.96V109.16C34.3245 108.056 35.0685 107.312 36.1725 107.312ZM52.5951 107.312C53.6751 107.312 54.4431 108.056 54.4431 109.16C54.4431 110.24 53.6751 111.008 52.5951 111.008H49.3551V122.96C49.3551 124.04 48.5871 124.808 47.5071 124.808C46.4271 124.808 45.6591 124.04 45.6591 122.96V111.008H42.4191C41.3391 111.008 40.5711 110.24 40.5711 109.16C40.5711 108.056 41.3391 107.312 42.4191 107.312H52.5951ZM63.5811 121.112C66.3651 121.112 68.6211 118.856 68.6211 116.048C68.6211 113.264 66.3651 111.008 63.5811 111.008C60.7731 111.008 58.5171 113.264 58.5171 116.048C58.5171 118.856 60.7731 121.112 63.5811 121.112ZM54.8211 116.048C54.8211 111.176 58.6851 107.312 63.5811 107.312C68.4531 107.312 72.3171 111.176 72.3171 116.048C72.3171 120.944 68.4531 124.808 63.5811 124.808C58.6851 124.808 54.8211 120.944 54.8211 116.048ZM84.5914 114.944C85.8394 115.976 86.4394 117.32 86.4394 119.048C86.4394 122.36 83.8954 124.832 80.4154 124.832C76.9594 124.832 74.3914 122.36 74.3914 119.048C74.3914 117.944 75.1594 117.2 76.2394 117.2C77.3434 117.2 78.0874 117.944 78.0874 119.048C78.0874 120.272 79.1194 121.136 80.4154 121.136C81.7354 121.136 82.7434 120.272 82.7434 119.048C82.7434 118.256 82.4794 117.944 82.2154 117.752C81.7834 117.368 80.9914 117.056 79.9834 116.792C77.5114 116.144 76.0474 114.32 76.0474 111.92C76.0474 109.304 78.0634 107.312 80.6554 107.312C83.3674 107.312 84.5194 108.608 85.0234 109.472C85.5754 110.408 85.3354 111.416 84.3754 111.992C83.4394 112.52 82.4314 112.256 81.8554 111.368C81.2074 110.456 79.7434 110.816 79.7434 111.92C79.7434 112.592 80.1754 113.024 80.9194 113.24C83.0794 113.816 84.0394 114.464 84.5914 114.944Z" fill="#1B2F50"/>
                <defs>
                    <filter id="filter0_d_17_32" x="67.2371" y="20.5403" width="65.0629" height="67.3586" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
                        <feFlood flood-opacity="0" result="BackgroundImageFix"/>
                        <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
                        <feMorphology radius="5" operator="dilate" in="SourceAlpha" result="effect1_dropShadow_17_32"/>
                        <feOffset dx="5" dy="4"/>
                        <feGaussianBlur stdDeviation="2"/>
                        <feComposite in2="hardAlpha" operator="out"/>
                        <feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.25 0"/>
                        <feBlend mode="normal" in2="BackgroundImageFix" result="effect1_dropShadow_17_32"/>
                        <feBlend mode="normal" in="SourceGraphic" in2="effect1_dropShadow_17_32" result="shape"/>
                    </filter>
                    <linearGradient id="paint0_linear_17_32" x1="73.6719" y1="0" x2="73.6719" y2="97.8563" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#0AD285"/>
                        <stop offset="1" stop-color="#10C57E"/>
                    </linearGradient>
                    <linearGradient id="paint1_linear_17_32" x1="90.8901" y1="3.73059" x2="89.8857" y2="97.7128" gradientUnits="userSpaceOnUse">
                        <stop offset="0.383" stop-color="#6A248B"/>
                        <stop offset="1" stop-color="#1A2C50"/>
                    </linearGradient>
                    <linearGradient id="paint2_linear_17_32" x1="118.152" y1="3.73059" x2="117.148" y2="97.7128" gradientUnits="userSpaceOnUse">
                        <stop offset="0.383" stop-color="#6A248B"/>
                        <stop offset="1" stop-color="#1A2C50"/>
                    </linearGradient>
                    <linearGradient id="paint3_linear_17_32" x1="73.6384" y1="69.7963" x2="73.517" y2="93.0001" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#0873E7"/>
                        <stop offset="1" stop-color="#0CB9F4"/>
                    </linearGradient>
                    <linearGradient id="paint4_linear_17_32" x1="51.0015" y1="19.5138" x2="96.773" y2="22.3835" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#FC404B"/>
                        <stop offset="1" stop-color="#D30442"/>
                    </linearGradient>
                    <linearGradient id="paint5_linear_17_32" x1="76.3981" y1="48.9281" x2="118.726" y2="50.5065" gradientUnits="userSpaceOnUse">
                        <stop offset="0.21587" stop-color="#19674E"/>
                        <stop offset="0.719519" stop-color="#64C21D"/>
                    </linearGradient>
                    <linearGradient id="paint6_linear_17_32" x1="51.5754" y1="25.5403" x2="59.467" y2="46.9195" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#1CEBF8"/>
                        <stop offset="1" stop-color="#06A8F4"/>
                    </linearGradient>
                    <linearGradient id="paint7_linear_17_32" x1="84.5811" y1="28.2665" x2="86.1594" y2="46.202" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#11E28F"/>
                        <stop offset="1" stop-color="#09B379"/>
                    </linearGradient>
                    <linearGradient id="paint8_linear_17_32" x1="94.1948" y1="25.54" x2="94.1948" y2="74.8986" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#7ECC16"/>
                        <stop offset="1" stop-color="#61BC17"/>
                    </linearGradient>
                    <linearGradient id="paint9_linear_17_32" x1="40.8447" y1="135.593" x2="102.256" y2="135.593" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#AADD13"/>
                        <stop offset="1" stop-color="#64C81A"/>
                    </linearGradient>
                </defs>
            </svg>-->
        </div>
    </div>

    <div class="page__title">Основные параметры оценки</div>

    <div class="parameters">
        <div class="parameters__item">
            <div class="parameters__item-inner d-flex items-center">
                Среднее время ответа 1-ого контакта:
                <div class="parameters__item-status" style="background-color: #73C356"></div>
                3 минуты;
            </div>
        </div>

        <div class="parameters__item">
            <div class="parameters__item-inner d-flex items-center">
                Среднее количество касаний с клиентом:
                <div class="parameters__item-status" style="background-color: #E4A03B"></div>
                5 касаний **;
            </div>
        </div>

        <div class="parameters__item d-flex items-center">
            <div class="parameters__item-inner d-flex items-center">
                Среднее время ответа 2-ого обращения:
                <div class="parameters__item-status" style="background-color: #C04D3D"></div>
                10 минут;
            </div>
        </div>
    </div>

    <div class="tips d-flex">
        <div class="tips__item d-flex items-center">
            <div class="tips__item-column d-flex items-center">
                * статистика за рабочее время менеджера с 08:00 до 22:00. Хорошее время обработки не более 2 мин
            </div>
        </div>
        <div class="tips__item d-flex items-center">
            <div class="tips__item-column d-flex items-center">
                ** подсчет по всем перепискам за выбранный период. Рекомендуемое количество касаний для продажи в переписке - от 5 касаний
            </div>
        </div>
    </div>

    <div class="page__title">Аналитика  с менеджерами</div>

    <div class="manager">
        <div class="manager__title">Менеджер Алия</div>

        <div class="parameters">
            <div class="parameters__item">
                <div class="parameters__item-inner d-flex items-center">
                    Среднее время ответа 1-ого контакта:
                    <div class="parameters__item-status" style="background-color: #73C356"></div>
                    3 минуты;
                </div>

            </div>

            <div class="parameters__item">
                <div class="parameters__item-inner d-flex items-center">
                    Среднее количество касаний с клиентом:
                    <div class="parameters__item-status" style="background-color: #E4A03B"></div>
                    5 касаний **;
                </div>
            </div>

            <div class="parameters__item">
                <div class="parameters__item-inner d-flex items-center">
                    Среднее время ответа 2-ого обращения:
                    <div class="parameters__item-status" style="background-color: #C04D3D"></div>
                    10 минут;
                </div>
            </div>
        </div>

        <div class="tips d-flex">
            <div class="tips__item d-flex items-center">
                <div class="tips__item-column d-flex items-center">
                    * статистика за рабочее время менеджера с 08:00 до 22:00
                </div>
            </div>
            <div class="tips__item d-flex items-center">
                <div class="tips__item-column d-flex items-center">
                    ** подсчет по всем перепискам за выбранный период
                </div>
            </div>
        </div>
    </div>

    <div class="page__title">Аналитика по менеджерам</div>

    <div class="reports">
        <div class="reports__top d-flex items-center justify-between">
            <div class="reports__top-info d-flex items-center">
                <span class="reports__top-manager">Менеджер Алия</span>
            </div>
        </div>

        <div class="report">
            <div class="report__inner d-flex items-center">
                <span class="report__title">Приветствие менеджера</span>
                <div class="report__info d-flex items-center justify-between">
                    <b>5</b>/ 10
                    <div class="report__info-status d-flex items-center" style="background-color: #E4A03B">средне</div>
                </div>
            </div>
        </div>

        <div class="report">
            <div class="report__inner d-flex items-center">
                <span class="report__title">Закрыл сделку</span>
                <div class="report__info d-flex items-center justify-between">
                    <b>10</b>/ 10
                    <div class="report__info-status d-flex items-center" style="background-color: #73C356">отлично</div>
                </div>
            </div>
        </div>

        <div class="report">
            <div class="report__inner d-flex items-center">
                <span class="report__title">Запросил номер WhatsApp</span>
                <div class="report__info d-flex items-center justify-between">
                    <b>5</b>/ 10
                    <div class="report__info-status d-flex items-center" style="background-color: #E4A03B">средне</div>
                </div>
            </div>
        </div>

        <div class="report">
            <div class="report__inner d-flex items-center">
                <span class="report__title">Вежливость</span>
                <div class="report__info d-flex items-center justify-between">
                    <b>3</b>/ 10
                    <div class="report__info-status d-flex items-center" style="background-color: #C14D3D">плохо</div>
                </div>
            </div>
        </div>
    </div>

    <div class="reports">
        <div class="reports__top d-flex items-center justify-between">
            <div class="reports__top-info d-flex items-center">
                <span class="reports__top-manager">Менеджер Айдар</span>
            </div>
        </div>

        <div class="report">
            <div class="report__inner d-flex items-center">
                <span class="report__title">Приветствие менеджера</span>
                <div class="report__info d-flex items-center justify-between">
                    <b>5</b>/ 10
                    <div class="report__info-status d-flex items-center" style="background-color: #E4A03B">средне</div>
                </div>
            </div>
        </div>

        <div class="report">
            <div class="report__inner d-flex items-center">
                <span class="report__title">Закрыл сделку</span>
                <div class="report__info d-flex items-center justify-between">
                    <b>10</b>/ 10
                    <div class="report__info-status d-flex items-center" style="background-color: #73C356">отлично</div>
                </div>
            </div>
        </div>

        <div class="report">
            <div class="report__inner d-flex items-center">
                <span class="report__title">Запросил номер WhatsApp</span>
                <div class="report__info d-flex items-center justify-between">
                    <b>5</b>/ 10
                    <div class="report__info-status d-flex items-center" style="background-color: #E4A03B">средне</div>
                </div>
            </div>
        </div>

        <div class="report">
            <div class="report__inner d-flex items-center">
                <span class="report__title">Вежливость</span>
                <div class="report__info d-flex items-center justify-between">
                    <b>3</b>/ 10
                    <div class="report__info-status d-flex items-center" style="background-color: #C14D3D">плохо</div>
                </div>
            </div>
        </div>
    </div>

    <div class="page__title">Анализ переписок</div>

    <div class="chats">
        {% for chat in data %}
        <div class="chat">
            <span class="chat__manager">Менеджер Алия</span>
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
    start_date = (datetime.now() - timedelta(days=6)).strftime("%d.%m.%Y")
    end_date = datetime.now().strftime("%d.%m.%Y")
    avito_account_name = analyze_all_chats[0]['avito_account_name'] if analyze_all_chats else "Неизвестно"
    return template.render(data=analyze_all_chats[0].get('analyze', []), avito_account_name=avito_account_name,
                           start_date=start_date, end_date=end_date)
