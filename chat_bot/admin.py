from django.db.models.query import QuerySet
from django.http import HttpRequest
from rangefilter.filters import DateRangeFilterBuilder

from django.contrib import admin
from django.db.models import Sum, F, ExpressionWrapper, FloatField
from django.template.response import TemplateResponse

from avito_account.admin_panel.filters import ContragentFilter
from chat_bot.filters import ChatIDFilter, ContactFilter
import chat_bot.models


@admin.register(chat_bot.models.ChatBotTask)
class ChatBotTaskAdmin(admin.ModelAdmin):
    ordering = ["-created_at"]
    list_filter = (
        ContragentFilter,
        'avito_account',
        'status',
        ChatIDFilter,
        ("created_at", DateRangeFilterBuilder()),
        ContactFilter,
    )
    search_fields = ("chat_id", "message_id", "answer_text", "text")

    def get_list_display(self, request):
        # Определяем, какие поля отображать в зависимости от прав пользователя
        base_display = [
            'created_at',
            'avito_account',
            'status',
            'cancel_reason',
            'is_incoming',
            'summary_sanded',
            'chat_shutdown_by_user',
            'chat_id',
            'message_id',
            'text',
            'answer_text',
            'mobile',
            'address',
        ]
        if request.user.is_superuser:
            base_display += ['tokens_completion', 'tokens_prompt']
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

    tokens_price.short_description = 'стоимость токенов'  # type: ignore

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        # Убедимся, что response — это TemplateResponse
        if isinstance(response, TemplateResponse) and response.context_data and 'cl' in response.context_data:
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


class ChatBotPromptInline(admin.StackedInline):
    model = chat_bot.models.AvitoPrompt
    extra = 0


class DialogTriggerInline(admin.StackedInline):
    model = chat_bot.models.DialogTrigger
    fields = [
        "title",
        "only_when_client_is_silent",
        "additional_condition",
        "message",
        "trigger",
        "delay_before_launch_trigger_sec",
    ]
    ordering = ["title"]
    extra = 0


@admin.register(chat_bot.models.AiChatBot)
class AiChatBotAdmin(admin.ModelAdmin):
    list_display = ["id", "account"]
    list_display_links = ["id", "account"]
    inlines = [ChatBotPromptInline, DialogTriggerInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[chat_bot.models.AiChatBot]:
        qs: QuerySet[chat_bot.models.AiChatBot] = super().get_queryset(request)

        if not request.user.is_superuser:
            qs = qs.filter(account__created_by=request.user)

        return qs
