from django.urls import path

from messaging.views import DurationWeekStatisticsView
from messaging.views_bad_messaging import BadMessagingWeekReportAllView

urlpatterns = [
    path('week_report/<str:avito_id>/', DurationWeekStatisticsView.as_view(), name='duration_week_stats'),
    path('bad_messaging_week_report_all_to_users/', BadMessagingWeekReportAllView.as_view(), name='bad_messaging_week_report_all'),
    # better to be duration_week_report instead week_report
]
