from django.urls import path
from messaging.views import BadMessagingWeekReportAllView, BadMessagingWeekReportIndividualView, \
    MonthReportIndividualView

urlpatterns = [
    path('bad_messaging_week_report_all_to_users/', BadMessagingWeekReportAllView.as_view(),
         name='bad_messaging_week_report_all'),
    path('bad_messaging_week_report_individual/<int:object_id>/', BadMessagingWeekReportIndividualView.as_view(),
         name='bad_messaging_week_individual'),
    # MONTH REPORT APIs
    path('month_report_individual/<int:avito_account_id>/', MonthReportIndividualView.as_view(),
         name='month_report_individual'),
]
