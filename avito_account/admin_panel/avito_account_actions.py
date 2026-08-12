import logging

from django.db.models import QuerySet

import avito_account.tasks
from avito_account.models.models import AvitoAccount
from chat_bot.utils import daily_report
from conversion.tasks import send_text_report_all_async_task
from messaging.tasks import bad_messaging_week_report_async_task, \
    month_report_json_getting_async_task

from utils.logging import TraceLogger

logger = logging.getLogger(__name__)


def celery_pdf_month_for_api_report(self, request, queryset):
    try:
        # TODO id you wont to debug it without celery don't forget
        #  month_report_json_getting_async_task changing
        month_report_json_getting_async_task.delay()
        self.message_user(request, "СЕЛЕРИ для АПИ месяц", level='success')
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"СЕЛЕРИ для АПИ месяц" f" Ошибка сервера - {e}", level='error')


celery_pdf_month_for_api_report.short_description = "СЕЛЕРИ для АПИ месяц"  # type: ignore


def run_pdf_week_report(self, request, queryset: QuerySet):
    object_ids = list(queryset.values_list('id', flat=True))

    try:
        bad_messaging_week_report_async_task.delay(only_for_users=object_ids)
        self.message_user(request, "ПДФ неделя отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"ПДФ неделя отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_pdf_week_report.short_description = "ПДФ неделя отчет отправить"  # type: ignore


def run_pdf_month_report(self, request, queryset):
    object_ids = list(queryset.values_list('id', flat=True))

    try:
        bad_messaging_week_report_async_task.delay(only_for_users=object_ids, period='month')
        self.message_user(request, "ПДФ месяц отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"ПДФ месяц отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_pdf_month_report.short_description = "ПДФ месяц отчет отправить"  # type: ignore


def run_pdf_all_report(self, request, queryset):
    try:
        bad_messaging_week_report_async_task.delay()
        self.message_user(request, "ПДФ ВСЕМ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"ПДФ ВСЕМ отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_pdf_all_report.short_description = "ПДФ ВСЕМ отчет отправить"  # type: ignore


def run_pdf_all_test_from_prod_report(self, request, queryset):
    try:
        bad_messaging_week_report_async_task.delay(test_from_prod=True)
        self.message_user(request, "ПДФ ВСЕМ ТЕСТ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"ПДФ ВСЕМ ТЕСТ отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_pdf_all_test_from_prod_report.short_description = "ПДФ ВСЕМ ТЕСТ отчет отправить"  # type: ignore


def run_txt_report(self, request, queryset):
    avito_account_ids = list(queryset.values_list('id', flat=True))
    try:
        send_text_report_all_async_task.delay(only_for_users=avito_account_ids)
        self.message_user(request, "ТЕКСТОВЫЙ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"ТЕКСТОВЫЙ ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_txt_report.short_description = "ТЕКСТОВЫЙ отчет отправить"  # type: ignore


def run_txt_all_report(self, request, queryset):
    try:
        send_text_report_all_async_task.delay()
        self.message_user(request, "ТЕКСТОВЫЙ ВСЕМ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"ТЕКСТОВЫЙ ВСЕМ ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_txt_all_report.short_description = "ТЕКСТОВЫЙ ВСЕМ отчет отправить"  # type: ignore


def run_txt_all_test_from_prod_report(self, request, queryset):
    try:
        send_text_report_all_async_task.delay(test_from_prod=True)
        self.message_user(request, "ТЕКСТОВЫЙ ТЕСТ ВСЕМ отчет успешно сгенерирован и отправлен.", level='success')
    except Exception as e:
        logger.error(f"ТЕКСТОВЫЙ ТЕСТ ВСЕМ ошибка при отправке отчета: {e}", exc_info=True)
        self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')


run_txt_all_test_from_prod_report.short_description = "ТЕКСТОВЫЙ ТЕСТ ВСЕМ отчет отправить"  # type: ignore


def run_daily_pdf_report(self, request, queryset: QuerySet[AvitoAccount]):
    tlogger = TraceLogger()

    try:
        tlogger.info(f"Run daily report for {len(queryset)} avito accounts")

        for account in queryset:
            daily_report.statistics_for_avito_account(account.pk, trace_id=tlogger.trace_id)

        self.message_user(request, f"Отправка отчета успешно начата", level='success')
    except Exception as e:
        tlogger.info({
            "title": "error when start daily pdf statistics",
            "error": e,
        })
        self.message_user(request, f"Отчет не удалось отправить. Ошибка серва - {e}", level='error')


run_daily_pdf_report.short_description = "Ежедневный пдф отчет"  # type: ignore


def update_avito_accounts_tokens(self, request, queryset: QuerySet[AvitoAccount]) -> None:
    tlogger = TraceLogger()
    errors: list[str] = []

    # for account in queryset:
    #     try:
    #         async_to_sync(account.update_refresh_token_async)(tlogger)
    #     except Exception as e:
    #         errors.append(f"Error when refresh token of '{account.name}'. Error: {e}")

    avito_account.tasks.update_tokens_task([account.pk for account in queryset])

    message = "Токены успешно обнвлены"
    level = "success"
    if errors:
        message = "\n".join(errors)
        level = "error"

    self.message_user(request, message, level=level)


update_avito_accounts_tokens.short_description = "Обновить токены"  # type: ignore


def actualize_avito_webhooks_subscriptions(self, request, queryset: QuerySet[AvitoAccount]) -> None:
    avito_account.tasks.actualize_avito_webhooks_subscriptions.delay(
    # avito_account.tasks.actualize_avito_webhooks_subscriptions(
        accounts_ids=[account.pk for account in queryset],
    )

    message = "Операция запушена"
    level = "success"

    self.message_user(request, message, level=level)


actualize_avito_webhooks_subscriptions.short_description = "Обновить подписки на уведомляния"  # type: ignore


def actualize_avito_items(self, request, queryset: QuerySet[AvitoAccount]) -> None:
    avito_account.tasks.actualize_avito_items.delay(
    # avito_account.tasks.actualize_avito_items(
        accounts_ids=[account.pk for account in queryset],
    )

    message = "Операция запущена"
    level = "success"

    self.message_user(request, message, level=level)


actualize_avito_items.short_description = "Обновить список объявлений"  # type: ignore


def disable_pdf_reports(self, request, queryset: QuerySet[AvitoAccount]) -> None:
    for account in queryset:
        account.weekly_pdf_report = False
    AvitoAccount.objects.bulk_update(queryset, fields=["weekly_pdf_report"])


disable_pdf_reports.short_description = "Отключить пдф отчеты"  # type: ignore


def disable_text_reports(self, request, queryset: QuerySet[AvitoAccount]) -> None:
    for account in queryset:
        account.weekly_text_report = False
    AvitoAccount.objects.bulk_update(queryset, fields=["weekly_text_report"])


disable_text_reports.short_description = "Отключить текстовые отчеты"  # type: ignore
