from celery import shared_task


@shared_task
def division_by_zero_task(request):
    division_by_zero = 1 / 0