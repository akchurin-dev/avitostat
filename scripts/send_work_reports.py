from work_reports.tasks import send_daily_report
from work_reports.tasks import send_weekly_report


def run():
    send_daily_report()
    send_weekly_report()
