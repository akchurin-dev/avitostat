from django.contrib import admin

import amo.models
import sandbox_chats.models


class InputChatMessageInline(admin.StackedInline):
    model = sandbox_chats.models.InputChatMessage
    extra = 0


class AmoChatbotInline(admin.TabularInline):
    model = amo.models.AmoChatbotSandboxInputChatLink
    extra = 0


@admin.register(sandbox_chats.models.InputChat)
class InputChatModel(admin.ModelAdmin):
    inlines = [
        InputChatMessageInline,
        AmoChatbotInline,
    ]
