from work_reports.tasks import send_daily_report


def run():
    send_daily_report()
