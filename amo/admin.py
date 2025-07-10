from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import redirect
import urllib.parse

import amo.models
import amo.schemas
import amo_a5client.models
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
    fields = ["name", "entity", "required_for_qualification", "isolated_check", "description"]
    extra = 0


class AmoPipelineStatusInline(admin.TabularInline):
    model = amo.models.AmoPipelineStatusChatbotLink
    fields = ["status", "check_qualification"]
    extra = 0


class AmoOriginInline(admin.TabularInline):
    model = amo.models.AmoChatbotOriginLink
    fields = ["origin"]
    extra = 0


class HandlebleNoteInline(admin.TabularInline):
    model = amo.models.HandlebleNote
    fields = ["author_name"]
    extra = 0


@admin.register(amo.models.AmoChatBot)
class AmoChatBotAdmin(admin.ModelAdmin):
    list_display = ["name", "account"]
    inlines = [
        FillableFieldInline,
        AmoPipelineStatusInline,
        AmoOriginInline,
        HandlebleNoteInline,
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[amo.models.AmoChatBot]:
        qs = super().get_queryset(request)

        if not request.user.is_superuser:
            qs = qs.filter(account__created_by=request.user)

        return qs


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
