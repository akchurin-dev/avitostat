from celery import shared_task
from django.urls import path

from deep_tests.tasks import division_by_zero_task
from deep_tests.views import BadMessagingWeekReportTestView, TelegramSenderTestView, TelegramDocumentSenderTestView, \
    BadMessagingWeekReportAllTestView

@shared_task
def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path('bad_messagging_week_report/<str:avito_accounts_id>/', BadMessagingWeekReportTestView.as_view(), name='bad_messaging_week'),
    path('bad_messaging_week_report_all_to_admin/', BadMessagingWeekReportAllTestView.as_view(), name='bad_messaging_week_all'),
    path('send_test_message', TelegramSenderTestView.as_view(), name='bad_messaging_week'),
    path('send_test_document', TelegramDocumentSenderTestView.as_view(), name='bad_messaging_week'),
    path('glitchtip-debug/', trigger_error),
    path('glitchtip-sentry-debug/', division_by_zero_task.delay()),
    ]
