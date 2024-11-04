import logging
from conversion.tasks import send_text_report_all_async_task
from messaging.tasks import bad_messaging_week_report_async_task
logger = logging.getLogger(__name__)


def run_pdf_report(self, request, queryset):
    object_ids = list(queryset.values_list('id', flat=True))

    try:
        bad_messaging_week_report_async_task(only_for_users=object_ids)
        self.message_user(request, "ПДФ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"ПДФ отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_pdf_report.short_description = "ПДФ отчет отправить"


def run_pdf_all_report(self, request, queryset):
    try:
        bad_messaging_week_report_async_task.delay()
        self.message_user(request, "ПДФ ВСЕМ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"ПДФ ВСЕМ отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_pdf_all_report.short_description = "ПДФ ВСЕМ отчет отправить"


def run_pdf_all_test_from_prod_report(self, request, queryset):
    try:
        bad_messaging_week_report_async_task.delay(test_from_prod=True)
        self.message_user(request, "ПДФ ВСЕМ ТЕСТ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"ПДФ ВСЕМ ТЕСТ отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_pdf_all_test_from_prod_report.short_description = "ПДФ ВСЕМ ТЕСТ отчет отправить"


def run_txt_report(self, request, queryset):
    avito_account_ids = list(queryset.values_list('id', flat=True))
    try:
        send_text_report_all_async_task(only_for_users=avito_account_ids)
        self.message_user(request, "ТЕКСТОВЫЙ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"ТЕКСТОВЫЙ ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_txt_report.short_description = "ТЕКСТОВЫЙ отчет отправить"


def run_txt_all_report(self, request, queryset):
    try:
        send_text_report_all_async_task.delay()
        self.message_user(request, "ТЕКСТОВЫЙ ВСЕМ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"ТЕКСТОВЫЙ ВСЕМ ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_txt_all_report.short_description = "ТЕКСТОВЫЙ ВСЕМ отчет отправить"


def run_txt_all_test_from_prod_report(self, request, queryset):
    try:
        send_text_report_all_async_task.delay(test_from_prod=True)
        self.message_user(request, "ТЕКСТОВЫЙ ТЕСТ ВСЕМ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"ТЕКСТОВЫЙ ТЕСТ ВСЕМ ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_txt_all_test_from_prod_report.short_description = "ТЕКСТОВЫЙ ТЕСТ ВСЕМ отчет отправить"
