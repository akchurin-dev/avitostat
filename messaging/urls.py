from django.urls import path

from messaging.views import DurationWeekStatisticsView
from messaging.views_bad_messaging import BadMessagingWeekReportAllView, BadMessagingWeekReportIndividualView

urlpatterns = [
    path('week_report/<str:avito_id>/', DurationWeekStatisticsView.as_view(), name='duration_week_stats'),
    path('bad_messaging_week_report_all_to_users/', BadMessagingWeekReportAllView.as_view(), name='bad_messaging_week_report_all'),
    path('bad_messaging_week_report_individual/<str:avito_id>', BadMessagingWeekReportIndividualView.as_view(), name='bad_messaging_week_individual'),
    # better to be duration_week_report instead week_report
]
