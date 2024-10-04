from django.urls import path

from ai_messaging.views import WebhookInboxView, SubscribeTestView

urlpatterns = [
    path('webhook_inbox/', WebhookInboxView.as_view(), name='webhook_inbox'),
    path('subscribe_test/', SubscribeTestView.as_view(), name='subscribe_test'),
]
