from django.urls import path

from deep_tests.views import BadMessagingWeekReportTestView, TelegramSenderTestView, TelegramDocumentSenderTestView, \
    BadMessagingWeekReportAllTestView

urlpatterns = [
    path('bad_messagging_week_report/<str:avito_accounts_id>/', BadMessagingWeekReportTestView.as_view(), name='bad_messaging_week'),
    path('bad_messaging_week_report_all_to_admin/', BadMessagingWeekReportAllTestView.as_view(), name='bad_messaging_week_all'),
    path('send_test_message', TelegramSenderTestView.as_view(), name='bad_messaging_week'),
    path('send_test_document', TelegramDocumentSenderTestView.as_view(), name='bad_messaging_week'),
]
