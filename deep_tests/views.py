from aiogram import types
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework.decorators import api_view
from rest_framework.generics import CreateAPIView
from rest_framework.generics import DestroyAPIView
from rest_framework.generics import RetrieveDestroyAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from telegram_bot import bot

from avito_account import oauth_utils
from avito_account.models import models as avito_account_models
from chat_bot import models as chat_bot_models
from deep_tests import serializers
from deep_tests.tasks import division_by_zero_task
from messaging.tasks import bad_messaging_report_by_period, bad_messaging_week_report_async_task


class TelegramSenderTestView(View):
    def get(self, request):
        bot.send_raw(chat_id="-1002061228822", text="TEST TEXT")


class TelegramDocumentSenderTestView(View):
    def get(self, request):
        bot.send_raw(
            chat_id="-1002061228822",
            function="send_document",
            document=types.FSInputFile("deep_tests/test.pdf"),
        )


class BadMessagingWeekReportTestView(View):
    async def get(self, request, *args, **kwargs):
        avito_accounts_id = kwargs.get("avito_accounts_id", None)
        await bad_messaging_report_by_period(test_from_prod=True, only_for_users=[avito_accounts_id])
        # TODO Придумать нормальные условия для 200 и других статусов, тк сейчас всегда 200
        return HttpResponse(status=200)


class BadMessagingWeekReportAllTestView(View):
    def get(self, request, *args, **kwargs):
        bad_messaging_week_report_async_task.delay(test_from_prod=True)
        # TODO Придумать нормальные условия для 200 и других статусов, тк сейчас всегда 200
        return HttpResponse(status=200)


class DivizionByZeroCeleryTaskTestView(View):
    def get(self, request, *args, **kwargs):
        division_by_zero_task.delay()
        return HttpResponse(status=200)


@api_view(["POST"])
def create_test_user(request: HttpRequest, *args, **kwargs) -> Response:
    username = f"test-user-{User.objects.count() + 1}"
    user = User.objects.create_user(username=username, password=username)
    return Response(status=201, data={
        "id": user.pk,
    })


class UserDestroyAPIView(DestroyAPIView):
    queryset = User.objects.all()


@api_view(["POST"])
def create_or_update_avito_account(request: Request, *args, **kwargs) -> Response:
    request_serializer = serializers.AvitoAccountRequestTestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    account_info = oauth_utils.get_avito_account_info(request_serializer.validated_data.get("access_token", ""))

    avito_account, created = avito_account_models.AvitoAccount.objects.update_or_create(
        id=account_info.get("id"),
        name=account_info.get("name"),
        profile_url=account_info.get("profile_url"),
        defaults={
            "telegram_id": request_serializer.validated_data.get("telegram_id"),
            "phone": "79991112233",
            "access_token": request_serializer.validated_data.get("access_token"),
            "refresh_token": request_serializer.validated_data.get("refresh_token"),
            "analytic_schema": None,
            "balance_alerting": False,
            "created_by_id": request_serializer.validated_data.get("created_by_id"),
        }
    )

    response_serializer = serializers.AvitoAccountResponseTestSerializer(avito_account)

    status = 201
    if not created:
        status = 200

    return Response(status=status, data=response_serializer.data)


class AvitoAccountRetrieveDestroyAPIView(RetrieveDestroyAPIView):
    queryset = avito_account_models.AvitoAccount.objects.all()
    serializer_class = serializers.AvitoAccountResponseTestSerializer


class AvitoAIChatBotCreateAPIView(CreateAPIView):
    queryset = chat_bot_models.AiChatBot.objects.all()
    serializer_class = serializers.AvitoAIChatBotTestSerializer


class AvitoAIChatBotRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = chat_bot_models.AiChatBot.objects.all()
    serializer_class = serializers.AvitoAIChatBotTestSerializer


class AvitoAIChatBotByAvitoAccountDestroyAPIView(DestroyAPIView):
    queryset = chat_bot_models.AiChatBot.objects.all()
    lookup_field = "avito_account_id"
    lookup_url_kwarg = "avito_account_pk"


class PrevSessionLastAvitoMessageAPIView(APIView):
    def get(self, request: Request):
        return self._current_value_response()

    def put(self, request: Request):
        value = request.query_params.get("value")
        if value is None:
            return Response(status=400, data={"message": "value is required"})

        settings.TEST_PREV_SESSION_LAST_AVITO_MESSAGE = value
        print("UPDATED TEST_PREV_SESSION_LAST_AVITO_MESSAGE TO", settings.TEST_PREV_SESSION_LAST_AVITO_MESSAGE)

        return self._current_value_response()

    def _current_value_response(self) -> HttpResponse:
        return HttpResponse(content=str(settings.TEST_PREV_SESSION_LAST_AVITO_MESSAGE).encode())


class UseGPTFlagAPIView(APIView):
    def get(self, request: HttpRequest) -> HttpResponse:
        return self._current_value_response()

    def put(self, request: Request) -> HttpResponse:
        value = request.query_params.get("value")
        if value is None:
            return Response(status=400, data={"message": "value is required"})

        settings.USE_GPT = value == "True"
        print("UPDATED USE_GPT TO", settings.USE_GPT)

        return self._current_value_response()

    def _current_value_response(self) -> HttpResponse:
        return HttpResponse(content=str(settings.USE_GPT).encode())
