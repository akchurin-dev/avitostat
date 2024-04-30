from django.contrib import admin
from django.contrib.admin import site

from conversion.models import Statistic

# Register your models here.
site.register(Statistic)
