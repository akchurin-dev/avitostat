from rangefilter.filters import DateRangeFilterBuilder

from chat_bot.filters import ChatIDFilter, ContactFilter
from chat_bot.models import ChatBotTask
from django.db.models import Sum, F, ExpressionWrapper, FloatField
from django.contrib import admin
from django.template.response import TemplateResponse
from avito_account.admin_panel.filters import ContragentFilter


class ChatBotTaskAdmin(admin.ModelAdmin):
    list_filter = (ContragentFilter, 'avito_account', ChatIDFilter, ("created_at", DateRangeFilterBuilder()), ContactFilter)
    search_fields = ("chat_id", "message_id", "answer_text", "text")

    def get_list_display(self, request):
        # Определяем, какие поля отображать в зависимости от прав пользователя
        base_display = ['chat_shutdown_by_user', 'chat_id', 'message_id', 'created_at', 'text', 'answer_text', 'mobile', 'address', 'summary_sanded']
        if request.user.is_superuser:
            base_display += ['tokens_completion', 'tokens_prompt']
        base_display += ['avito_account', ]
        return base_display

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Аннотация для вычисления стоимости токенов в базе данных
        queryset = qs.annotate(
            tokens_price=ExpressionWrapper(
                F('tokens_prompt') * 0.000125 + F('tokens_completion') * 0.0005,
                output_field=FloatField()
            )
        )
        return queryset.order_by('-created_at__date','created_at__time', 'chat_id')

    def tokens_price(self, obj):
        tokens_price = round(obj.tokens_prompt * 0.000125 + obj.tokens_completion * 0.0005, 1)
        return tokens_price

    tokens_price.short_description = 'стоимость токенов'

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        # Убедимся, что response — это TemplateResponse
        if isinstance(response, TemplateResponse) and 'cl' in response.context_data:
            # Получаем отфильтрованный queryset
            qs = response.context_data['cl'].queryset

            # Суммируем нужные поля и аннотированное поле
            total_tokens_completion = qs.aggregate(Sum('tokens_completion'))['tokens_completion__sum'] or 0
            total_tokens_prompt = qs.aggregate(Sum('tokens_prompt'))['tokens_prompt__sum'] or 0
            total_tokens_price = qs.aggregate(Sum('tokens_price'))['tokens_price__sum'] or 0

            # Передаем итоговые суммы в контекст
            response.context_data['total_tokens_completion'] = total_tokens_completion
            response.context_data['total_tokens_prompt'] = total_tokens_prompt
            response.context_data['total_tokens_price'] = round(total_tokens_price, 1)

        return response


admin.site.register(ChatBotTask, ChatBotTaskAdmin)
