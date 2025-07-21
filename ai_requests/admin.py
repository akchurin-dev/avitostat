from django.contrib import admin

import ai_requests.models


@admin.register(ai_requests.models.AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    list_display = ["tag", "model", "tokens_completion", "tokens_prompt", "created_at"]
