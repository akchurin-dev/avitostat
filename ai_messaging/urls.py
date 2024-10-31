from django.urls import path

from ai_messaging.views import WebhookInboxView, SubscribeView, StopSubscribeView, CheckSubscribtionsView

urlpatterns = [
    path('webhook_inbox', WebhookInboxView.as_view(), name='webhook_inbox'),
    path('subscribe/', SubscribeView.as_view(), name='subscribe'),
    path('stop_subscribe/', StopSubscribeView.as_view(), name='stop_subscribe'),
    path('check_subscriptions/', CheckSubscribtionsView.as_view(), name='check_subscriptions'),
]
