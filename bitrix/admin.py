from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest

from bitrix import models as bitrix_models


@admin.register(bitrix_models.BitrixAccount)
class BitrixAccountAdmin(admin.ModelAdmin):
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)

        if not request.user.is_superuser:
            qs = qs.filter(owner=request.user)

        return qs


@admin.register(bitrix_models.AIChatBot)
class AIChatBotAdmin(admin.ModelAdmin):
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)

        if not request.user.is_superuser:
            qs = qs.filter(bitrix_account__owner=request.user)

        return qs
