from work_reports.tasks import send_daily_report
from work_reports.tasks import send_weekly_report
from work_reports.tasks import send_report_for_last_30_days


def run():
    send_daily_report()
    send_weekly_report()
    send_report_for_last_30_days()
