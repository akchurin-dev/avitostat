from django.contrib import admin
from django.contrib.admin import site

from conversion.models import Statistic


class StatisticAdmin(admin.ModelAdmin):
    #TODO добавить нормальную фильтрацию по дате
    #TODO добавить фильтрацию по аккаунт/объявление

    list_filter = ('item', 'date')


# Register your models here.
# site.register(Statistic, StatisticAdmin)
