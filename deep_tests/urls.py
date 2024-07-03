from django.urls import path

from deep_tests.views import BadMessagingWeekReportView, TelegramSenderTestView

urlpatterns = [
    path('bad_messagging_week_report/<str:avito_accounts_id>/', BadMessagingWeekReportView.as_view(), name='bad_messaging_week'),
    path('send_test_message', TelegramSenderTestView.as_view(), name='bad_messaging_week'),
]
