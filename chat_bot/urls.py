from django.urls import path
from chat_bot.views import WebhookInboxView, SubscribeView, StopSubscribeView, CheckSubscribtionsView

urlpatterns = [
    path('webhook_inbox', WebhookInboxView.as_view(), name='webhook_inbox'),
    path('subscribe/', SubscribeView.as_view(), name='subscribe'),  # подписка в ручном режимет постманом для тестов
    path('stop_subscribe/', StopSubscribeView.as_view(), name='stop_subscribe'),  # подписка в ручном режимет постманом для тестов
    path('check_subscriptions/', CheckSubscribtionsView.as_view(), name='check_subscriptions'),  # подписка в ручном режимет постманом для тестов
]
