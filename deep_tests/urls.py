from celery import shared_task
from django.urls import path

from deep_tests.tasks import division_by_zero_task
from deep_tests import views


@shared_task
def trigger_error():
    division_by_zero = 1 / 0


urlpatterns = [
    path('bad_messagging_week_report/<str:avito_accounts_id>/', views.BadMessagingWeekReportTestView.as_view(), name='bad_messaging_week'),
    path('bad_messaging_week_report_all_to_admin/', views.BadMessagingWeekReportAllTestView.as_view(), name='bad_messaging_week_all'),
    path('send_test_message', views.TelegramSenderTestView.as_view(), name='bad_messaging_week'),
    path('send_test_document', views.TelegramDocumentSenderTestView.as_view(), name='bad_messaging_week'),
    path('rollbar-debug/', trigger_error),
    path('rollbar-sentry-debug/', views.DivizionByZeroCeleryTaskTestView.as_view()),
    path('user', views.create_test_user),
    path('user/<int:pk>', views.UserDestroyAPIView.as_view()),
    path('avito-account', views.create_or_update_avito_account),
    path('avito-account/<int:pk>', views.AvitoAccountRetrieveDestroyAPIView.as_view()),
    path('avito-ai-chat-bot', views.AvitoAIChatBotCreateAPIView.as_view()),
    path('avito-ai-chat-bot/<int:pk>', views.AvitoAIChatBotRetrieveUpdateDestroyAPIView.as_view()),
    path('avito-ai-chat-bot-by-avito-account/<int:avito_account_pk>', views.AvitoAIChatBotByAvitoAccountDestroyAPIView.as_view()),
    path('prev-session-last-avito-message', views.PrevSessionLastAvitoMessageAPIView.as_view()),
    path('use-gpt-flag', views.UseGPTFlagAPIView.as_view()),
]
