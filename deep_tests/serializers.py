from rest_framework import serializers

from avito_account.models import models as avito_account_models
from chat_bot import models as chat_bot_models


class AvitoAccountRequestTestSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    telegram_id = serializers.CharField()
    created_by_id = serializers.IntegerField()


class AvitoAccountResponseTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = avito_account_models.AvitoAccount
        fields = (
            "id",
            "name",
            "telegram_id",
            "access_token",
            "refresh_token",
            "created_by_id",
        )


class AvitoAIChatBotTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = chat_bot_models.AiChatBot
        fields = (
            "id",
            "avito_account",
            "is_active",
            "total_info",
            "rules",
            "checkpoints",
            "waiting_minutes",
            "shutdown_after_manager",
            "work_time_from",
            "work_time_to",
            "statistics_daily_report",
            "histories_closed",
            "histories_open",
        )
