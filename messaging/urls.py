from django.urls import path

from messaging.views import DurationStatisticsView, WebhookView

urlpatterns = [
    path('week_report/<str:telegram_id>/', DurationStatisticsView.as_view(), name='chat_list'),
    path('webhook', WebhookView.as_view(), name='webhook'),
]
