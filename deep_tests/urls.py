from django.urls import path

from deep_tests.views import BadMessagingWeekReportView, TelegramSenderTestView, TelegramDocumentSenderTestView, \
    BadMessagingWeekReportAllView

urlpatterns = [
    path('bad_messagging_week_report/<str:avito_accounts_id>/', BadMessagingWeekReportView.as_view(), name='bad_messaging_week'),
    path('bad_messaging_week_report_all_to_admin/', BadMessagingWeekReportAllView.as_view(), name='bad_messaging_week_all'),
    path('send_test_message', TelegramSenderTestView.as_view(), name='bad_messaging_week'),
    path('send_test_document', TelegramDocumentSenderTestView.as_view(), name='bad_messaging_week'),
]
