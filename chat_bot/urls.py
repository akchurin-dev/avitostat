from django.urls import path

import chat_bot.views

urlpatterns = [
    path('webhook_inbox', chat_bot.views.WebhookInboxViewClass.as_view(), name='webhook_inbox'), # непосредственно в кор логике задествовано
    path('statistics_daily_report/', chat_bot.views.StatisticsDailyReportView.as_view(), name='statistics_daily_report'),  # применяется для ручного тестирования
    path('chat_summary_report/', chat_bot.views.SummarySenderView.as_view(), name='chat_summary_report'), # применяется для ручного тестирования
    path('multiple_files_sender/', chat_bot.views.MiltipleFilesSenderTestView.as_view()), # применяется для ручного тестирования
]
