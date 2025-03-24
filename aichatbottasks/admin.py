from django.contrib import admin

from aichatbottasks import models as aichatbottask_models


@admin.register(aichatbottask_models.Task)
class TaskAdmin(admin.ModelAdmin):
    pass
