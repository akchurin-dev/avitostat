from django.urls import path
from chat_bot.views import WebhookInboxView, SubscribeView, StopSubscribeView, CheckSubscribtionsView, \
    HistoryReportView, StatisticsDailyReportView

urlpatterns = [
    path('webhook_inbox', WebhookInboxView.as_view(), name='webhook_inbox'), # непосредственно в кор логике задествовано
    path('subscribe/', SubscribeView.as_view(), name='subscribe'),  # подписка в ручном режимет постманом для тестов # применяется в даминке
    path('stop_subscribe/', StopSubscribeView.as_view(), name='stop_subscribe'),  # подписка в ручном режимет постманом для тестов # применяется в даминке
    path('check_subscriptions/', CheckSubscribtionsView.as_view(), name='check_subscriptions'),  # подписка в ручном режимет постманом для тестов # применяется в даминке
    path('statistics_daily_report/', StatisticsDailyReportView.as_view(), name='statistics_daily_report'),  # применяется для ручного тестирования
    path('chat_summary_report/', HistoryReportView.as_view(), name='chat_summary_report'), # применяется для ручного тестирования



]
