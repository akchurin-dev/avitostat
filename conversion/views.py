import datetime

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from avito_account.api.get_operations import get_active_operations_for_period
from avito_account.models import AvitoAccount
from conversion.api import get_statistics_for_period

operations = [{'amountBonus': 0,
               'amountRub': 640,
               'amountTotal': 640,
               'itemId': 3723565374,
               'operationName': 'Продвижение, 160 ₽ × 10 дней',
               'operationType': 'резервирование средств под услугу',
               'serviceId': 111, 'serviceName': 'Продвижение',
               'serviceType': 'bbip',
               'updatedAt': '2024-04-29T15:34:27+03:00',
               'amount_per_day': 160,
               'duration': 10,
               'finishAt': '2024-05-09T15:34:27+03:00',
               'days_active_in_period': 8},
              {'amountBonus': 0,
               'amountRub': 640,
               'amountTotal': 640,
               'itemId': 3723371485,
               'operationName': 'Продвижение, 160 ₽ × 10 дней',
               'operationType': 'резервирование средств под услугу',
               'serviceId': 111, 'serviceName': 'Продвижение',
               'serviceType': 'bbip',
               'updatedAt': '2024-04-29T15:33:55+03:00',
               'amount_per_day': 160,
               'duration': 10,
               'finishAt': '2024-05-09T15:33:55+03:00',
               'days_active_in_period': 8},
              {'amountBonus': 0,
               'amountRub': 448,
               'amountTotal': 448,
               'itemId': 3722666047,
               'operationName': 'Продвижение,'
                                ' 160 ₽ × 7 дней',
               'operationType': 'резервирование средств под услугу',
               'serviceId': 111,
               'serviceName': 'Продвижение',
               'serviceType': 'bbip',
               'updatedAt': '2024-05-08T15:32:22+03:00',
               'amount_per_day': 160,
               'duration': 7,
               'finishAt': '2024-05-15T15:32:22+03:00',
               'days_left_active_total': 6,
               'days_active_in_period': 1},
              {'amountBonus': 0,
               'amountRub': 320,
               'amountTotal': 320,
               'itemId': 3723565374,
               'operationName': 'Продвижение, 160 ₽ × 5 дней',
               'operationType': 'резервирование средств под услугу',
               'serviceId': 111, 'serviceName': 'Продвижение',
               'serviceType': 'bbip',
               'updatedAt': '2024-05-08T15:31:52+03:00',
               'amount_per_day': 160,
               'duration': 5,
               'finishAt': '2024-05-13T15:31:52+03:00',
               'days_left_active_total': 4,
               'days_active_in_period': 1},
              {'amountBonus': 0,
               'amountRub': 320,
               'amountTotal': 320,
               'itemId': 3755005465,
               'operationName': 'Продвижение, 160 ₽ × 5 дней',
               'operationType': 'резервирование средств под услугу',
               'serviceId': 111,
               'serviceName': 'Продвижение',
               'serviceType': 'bbip',
               'updatedAt': '2024-05-08T15:31:15+03:00',
               'amount_per_day': 160,
               'duration': 5,
               'finishAt': '2024-05-13T15:31:15+03:00',
               'days_left_active_total': 4,
               'days_active_in_period': 1},
              {'amountBonus': 0,
               'amountRub': 320,
               'amountTotal': 320,
               'itemId': 3755402557,
               'operationName': 'Продвижение, 160 ₽ × 5 дней',
               'operationType': 'резервирование средств под услугу',
               'serviceId': 111,
               'serviceName': 'Продвижение',
               'serviceType': 'bbip',
               'updatedAt': '2024-05-08T15:30:57+03:00',
               'amount_per_day': 160,
               'duration': 5,
               'finishAt': '2024-05-13T15:30:57+03:00',
               'days_left_active_total': 4,
               'days_active_in_period': 1}]


def get_week_number():
    today = datetime.datetime.now()
    week_number = (today.day - 1) // 7
    return week_number


@method_decorator(csrf_exempt, name='dispatch')
class Test(View):
    def get(self, request, *args, **kwargs):
        avito_account = AvitoAccount.objects.filter(id=203199629).last()
        statistics = get_statistics_for_period(avito_account, period="week")  # Здесь токен рефрешится если он просрочен
        operations = get_active_operations_for_period(avito_account, period="week")
        week_number = get_week_number()

        costs_merged = {}
        if operations:
            for operation in operations:
                itemId = operation.get('itemId')
                coast = costs_merged.get(itemId)
                if coast is None:
                    costs_merged[itemId] = operation.get("period_coast")
                else:
                    costs_merged[itemId] = coast + operation.get("period_coast")



        conversions = {}
        if statistics:
            for statistic in statistics:
                itemId = statistic.get("itemId", None)
                if itemId:
                    conversion_item = conversions.get(itemId, None)
                    if conversion_item is None:
                        conversions[itemId] = {
                                'uniqContacts': statistic.get("stats")[week_number].get("uniqContacts"),
                                'uniqFavorites': statistic.get("stats")[week_number].get("uniqFavorites"),
                                'uniqViews': statistic.get("stats")[week_number].get("uniqViews"),
                        }

                        coast = costs_merged.get(itemId)
                        if coast:
                            # TODO учесть что бывают нули
                            conversions[itemId] = conversions[itemId] + {
                                "amount_per_contact": coast / statistic.get("stats")[week_number].get("uniqContacts"),
                                "amount_per_favorite": coast / statistic.get("stats")[week_number].get("uniqFavorites"),
                                "amount_per_view": coast / statistic.get("stats")[week_number].get("uniqViews"),
                            }


        return JsonResponse(status=200, data={"message": "Test success"})
