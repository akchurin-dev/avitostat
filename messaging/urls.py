from django.urls import path

from messaging.views import DurationWeekStatisticsView, BadMessagingWeekView

urlpatterns = [
    path('week_report/<str:telegram_id>/', DurationWeekStatisticsView.as_view(), name='duration_week_stats'),
    # better to be duration week report instead week_report
    path('bad_messagging_report', BadMessagingWeekView.as_view(), name='bad_messaging_week'),
]
