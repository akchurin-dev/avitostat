from django.contrib import admin
from django.contrib.admin import site
from django.db.models import Q

from avito_account.models import AvitoAccount
import logging
from conversion.models import Operation
from messaging.tasks import bad_messaging_week_report_async
# Настройка логирования
logger = logging.getLogger(__name__)

class OperationInline(admin.TabularInline):
    model = Operation
    extra = 0


class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'status', 'address', 'category', 'url')
    list_filter = ('avito_account', 'status')
    inlines = [OperationInline, ]


class AvitoAccountAdmin(admin.ModelAdmin):
    list_display = ('company', 'name', 'telegram_id', 'phone', 'profile_url')
    readonly_fields = ('id',)
    # exclude = ('access_token', 'refresh_token')

    def get_queryset(self, request):
        if request.user.is_superuser:
            queryset = super().get_queryset(request)
        else:
            queryset = super().get_queryset(request).filter(Q(company_id=request.user.pk) | Q(company_id=None))
        return queryset

    def has_add_permission(self, request):
        return False

    def get_fields(self, request, obj=None):  # Only for view id in details and hide in list
        fields = super().get_fields(request, obj)
        if obj is not None and 'id' not in fields:
            fields = ['id'] + list(fields)
        return fields

    def get_readonly_fields(self, request, obj=None):  # Only for view id in details and hide in list
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is not None and 'id' not in readonly_fields:
            readonly_fields = ['id'] + list(readonly_fields)
        return readonly_fields

        # Определение действия для экшн кнопки

    actions = ['run_weekly_report']

    def run_weekly_report(self, request, queryset):
        object_ids = list(queryset.values_list('id', flat=True))

        try:
            # Вызываем задачу Celery, передавая айдишники объектов
            bad_messaging_week_report_async.delay(only_for_users=object_ids)

            # Опционально, добавьте сообщение об успешном выполнении действия
            self.message_user(request, "Отчет успешно сгенерирован и отправлен.", level='success')
        except Exception as e:
            logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
            self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')

    run_weekly_report.short_description = "Отправить недельный отчет"


site.register(AvitoAccount, AvitoAccountAdmin)
# site.register(Item, ItemAdmin)
# site.register(ServiceType)
# site.register(Operation)
