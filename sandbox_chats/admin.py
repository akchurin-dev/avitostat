from django.contrib import admin

import amo.admin
import sandbox_chats.models


class InputChatInline(admin.TabularInline):
    model = sandbox_chats.models.SandboxInputChat
    extra = 0
    readonly_fields = "__all__"


class OutputChatInline(admin.StackedInline):
    model = sandbox_chats.models.SandboxOutputChat
    extra = 0


@admin.register(sandbox_chats.models.SandboxSession)
class SandboxSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "created_at",
        "status",
    ]

    readonly_fields = "__all__"

    inlines = [
        InputChatInline,
        amo.admin.AmoChatbotSandboxSessionLinkInline,
        OutputChatInline,
    ]

    ordering = ["-created_at"]


class ChatMessageInline(admin.TabularInline):
    model = sandbox_chats.models.ChatMessage
    extra = 0

    fields = [
        "author",
        "text",
        "image_url",
        "created_at",
    ]

    readonly_fields = ["created_at"]
    ordering = ["created_at", "id"]


@admin.register(sandbox_chats.models.SandboxInputChat)
class InputChatAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "created_at",
    ]

    inlines = [
        ChatMessageInline,
        amo.admin.AmoChatbotSandboxInputChatLinkInline,
    ]

    ordering = ["-created_at"]


class TextAnswerInline(admin.StackedInline):
    model = sandbox_chats.models.SandboxTextAnswer
    extra = 0
    readonly_fields = "__all__"


@admin.register(sandbox_chats.models.SandboxOutputChat)
class OutputChatAdmin(admin.ModelAdmin):
    list_display = [
        "session",
        "input_chat",
        "created_at",
    ]

    readonly_fields = "__all__"

    inlines = [
        ChatMessageInline,
        TextAnswerInline,
    ]

    ordering = ["-created_at"]
