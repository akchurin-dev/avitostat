from django.contrib import admin

import ai_requests.models


@admin.register(ai_requests.models.AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    pass
