from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import redirect
import urllib.parse

import amo.models
import amo.schemas
import amo.tasks
import amo_a5client.models
from amo.utils import amo_sandbox
from base import settings


class AvitoAccountInline(admin.TabularInline):
    model = amo_a5client.models.AmoAvitoAccountsLink
    fields = ["avito_account", "is_active"]
    extra = 0


class AmoChatCreateConfigInline(admin.TabularInline):
    model = amo.models.AmoChatCreateConfig
    fields = [
        "source",
        "phone_number_field",
        "channel_id",
    ]
    extra = 0


@admin.register(amo.models.AmoAccount)
class AmoAccountAdmin(admin.ModelAdmin):
    fields = [
        "amo_id",
        "name",
        "telegram_id",
        "domain",
        "amojo_id",
        "amo_login",
        "amo_password",
        "created_by",
        "created_at",
        "updated_at",
    ]
    readonly_fields = [
        "amo_id",
        "name",
        "domain",
        "amojo_id",
        "created_at",
        "updated_at",
    ]
    list_display = [
        "amo_id",
        "name",
        "domain",
        "created_by",
        "created_at",
        "updated_at",
    ]
    inlines = [
        AvitoAccountInline,
        AmoChatCreateConfigInline,
    ]

    def add_view(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.pk is None:
            return HttpResponse(status=401)

        params = {
            "client_id": settings.AMO_INTEGRATION_ID,
            "mode": "popup",
            "state": amo.schemas.OauthStateSchema(created_by_id=request.user.pk).model_dump_json(),
        }
        amo_oauth_link = "https://www.amocrm.ru/oauth?" + urllib.parse.urlencode(params)
        return redirect(to=amo_oauth_link)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)

        if not request.user.is_superuser:
            qs = qs.filter(created_by=request.user)

        return qs

    def actualize_amo_fields(self, request, queryset: QuerySet[amo.models.AmoAccount]) -> None:
        accounts_ids: list[int] = [account.amo_id for account in queryset]
        amo.tasks.actualize_amo_fields.delay(accounts_ids)
        # amo.tasks.actualize_amo_fields(accounts_ids)
        self.message_user(request, "Операция запущена", level="success")
    actualize_amo_fields.short_description = "Обновить Amo-поля"  # type: ignore

    actions = [actualize_amo_fields]


@admin.register(amo.models.AmoOrigin)
class AmoOriginAdmin(admin.ModelAdmin):
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        amo_accounts = amo.models.AmoAccount.objects.filter(created_by=request.user)
        qs = qs.filter(account__in=amo_accounts)

        return qs


class FillableFieldInline(admin.TabularInline):
    model = amo.models.FillableField
    fields = [
        "name",
        "entity",
        "required_for_qualification",
        "description",
    ]
    extra = 0


class AmoPipelineStatusInline(admin.TabularInline):
    model = amo.models.AmoPipelineStatusChatbotLink
    fields = ["status", "check_qualification"]
    extra = 0


class AmoOriginInline(admin.TabularInline):
    model = amo.models.AmoChatbotOriginLink
    fields = ["origin"]
    extra = 0


class AmoPromptInline(admin.StackedInline):
    model = amo.models.AmoPrompt
    extra = 0


class AmoCaseTypeInline(admin.StackedInline):
    model = amo.models.AmoCaseType
    extra = 0


class SandboxChatInline(admin.TabularInline):
    model = amo.models.AmoChatbotSandboxInputChatLink
    extra = 0


@admin.register(amo.models.AmoChatBot)
class AmoChatBotAdmin(admin.ModelAdmin):
    list_display = ["name", "account"]
    inlines = [
        AmoPromptInline,
        FillableFieldInline,
        AmoPipelineStatusInline,
        AmoOriginInline,
        AmoCaseTypeInline,
        SandboxChatInline,
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[amo.models.AmoChatBot]:
        qs = super().get_queryset(request)

        if not request.user.is_superuser:
            qs = qs.filter(account__created_by=request.user)

        return qs

    def run_sandbox_session(self, request, queryset: QuerySet[amo.models.AmoChatBot]) -> None:
        for chatbot in queryset:
            amo_sandbox.run_sandbox_session.delay(chatbot.pk)

        self.message_user(request, "Операция запущена", level="success")
    run_sandbox_session.short_description = "Запустить в песочнице"  # type: ignore

    actions = [run_sandbox_session]


@admin.register(amo.models.AmoChatBotTask)
class AmoChatBotTaskAdmin(admin.ModelAdmin):
    ordering = ["-created_at"]
    list_display = [
        "id",
        "status",
        "account",
        "text",
        "answer_text",
        "tokens_completion",
        "tokens_prompt",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)

        if not request.user.is_superuser:
            qs = qs.filter(account__created_by=request.user)

        return qs


class AmoSandboxSessionChatInline(admin.TabularInline):
    model = amo.models.AmoSandboxSessionChat
    extra = 0


@admin.register(amo.models.AmoSandboxSession)
class AmoSandboxSessionAdmin(admin.ModelAdmin):
    list_display = [
        "chatbot",
        "created_at",
        "finished",
    ]
    inlines = [AmoSandboxSessionChatInline]


class AmoSandboxOutputChatMessageInline(admin.TabularInline):
    model = amo.models.AmoSandboxOutputChatMessage
    extra = 0
    ordering = ["created_at"]


class AmoSandboxAnswerInline(admin.TabularInline):
    model = amo.models.AmoSandboxAnswer
    extra = 0


@admin.register(amo.models.AmoSandboxSessionChat)
class AmoSandboxSessionChat(admin.ModelAdmin):
    inlines = [
        AmoSandboxOutputChatMessageInline,
        AmoSandboxAnswerInline,
    ]
