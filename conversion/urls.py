from django.urls import path

from conversion.views import WeekReportView

urlpatterns = [
    #TODO сделать недельный отчёт по айди аккаунта, те передаем айдишник,
    #TODO и формируются отчёты на все авито аккаунты данной компании
    path('week_report/', WeekReportView.as_view(), name='week_report'),
]
