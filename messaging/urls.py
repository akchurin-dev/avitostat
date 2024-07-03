from django.urls import path

from messaging.views import DurationWeekStatisticsView
from messaging.views_test import TelegramSenderTestView

urlpatterns = [
    path('week_report/<str:telegram_id>/', DurationWeekStatisticsView.as_view(), name='duration_week_stats'),
    # better to be duration_week_report instead week_report
    # path('bad_messagging_week_report/<str:avito_accounts_id>/', BadMessagingWeekReportView.as_view(), name='bad_messaging_week'),
    path('send_test_message', TelegramSenderTestView.as_view(), name='bad_messaging_week'),
]
