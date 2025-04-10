import urllib.parse
from django.contrib import admin
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import redirect
import urllib.parse

import amo.models
import amo.schemas
from base import settings


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

    def add_view(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.pk is None:
            return HttpResponse(status=401)

        params = {
            "client_id": settings.AMO_INTEGRATION_ID,
            "mode": "popup",
            "state": amo.schemas.OauthStateSchema(created_by_id=request.user.pk).model_dump_json(),
        }
        amo_oauth_link = f"https://www.amocrm.ru/oauth?" + urllib.parse.urlencode(params)
        return redirect(to=amo_oauth_link)


class FillableFieldInline(admin.TabularInline):
    model = amo.models.FillableField
    fields = ["name", "description", "entity"]
    extra = 0


class AmoPipelineStatusInline(admin.TabularInline):
    model = amo.models.AmoPipelineStatus
    fields = ["pipeline_name", "name"]
    readonly_fields = ["pipeline_name", "name"]
    can_delete = False
    extra = 0


@admin.register(amo.models.AmoChatBot)
class AmoChatBotAdmin(admin.ModelAdmin):
    list_display = ["name", "account"]
    inlines = [FillableFieldInline, AmoPipelineStatusInline]


@admin.register(amo.models.AmoPipelineStatus)
class AmoPipelineStatusAdmin(admin.ModelAdmin):
    fields = ["pipeline_name", "name", "chat_bot"]
    readonly_fields = ["pipeline_name", "name"]
    list_display = ["pipeline_name", "name", "chat_bot"]
    list_select_related = ["chat_bot"]
    list_editable = ["chat_bot"]


@admin.register(amo.models.AmoChatBotTask)
class AmoChatBotTaskAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "account", "text", "answer_text", "tokens_completion", "tokens_prompt"]
