from django.urls import path

from messaging.views import DurationStatisticsView

urlpatterns = [
    path('week_report/<str:telegram_id>/', DurationStatisticsView.as_view(), name='chat_list'),
]