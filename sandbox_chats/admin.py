from django.contrib import admin

import amo.admin
import sandbox_chats.models


class SandboxSessionInputChatLinkInline(admin.TabularInline):
    model = sandbox_chats.models.SandboxSessionInputChatLink
    extra = 0

    readonly_fields = [
        "session",
        "chat",
    ]


class OutputChatInline(admin.StackedInline):
    model = sandbox_chats.models.SandboxOutputChat
    extra = 0

    fields = [
        "session",
        "input_chat",
        "answer_requirements",
        "avg_rate",
        "min_rate",
        "max_rate",
        "created_at",
    ]

    readonly_fields = fields


@admin.register(sandbox_chats.models.SandboxSession)
class SandboxSessionAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "status",
    ]

    fields = [
        "status",
        "created_at",
    ]

    readonly_fields = fields

    inlines = [
        SandboxSessionInputChatLinkInline,
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

    ordering = ["created_at", "id"]


@admin.register(sandbox_chats.models.SandboxInputChat)
class InputChatAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "created_at",
    ]

    fields = [
        "title",
        "answer_requirements",
        "created_at",
    ]

    readonly_fields = ["created_at"]

    inlines = [
        ChatMessageInline,
        amo.admin.AmoChatbotSandboxInputChatLinkInline,
    ]

    ordering = ["-created_at"]


class TextAnswerInline(admin.StackedInline):
    model = sandbox_chats.models.SandboxTextAnswer
    extra = 0

    fields = [
        "text",
        "rate",
        "rate_explanation",
    ]

    readonly_fields = [
        "text",
        "rate",
        "rate_explanation",
    ]


class OutputChatMessageInline(ChatMessageInline):
    readonly_fields = [
        "author",
        "text",
        "image_url",
        "created_at",
    ]


@admin.register(sandbox_chats.models.SandboxOutputChat)
class OutputChatAdmin(admin.ModelAdmin):
    list_display = [
        "session",
        "input_chat",
        "avg_rate",
        "min_rate",
        "max_rate",
        "created_at",
    ]

    fields = [
        "session",
        "answer_requirements",
        "avg_rate",
        "min_rate",
        "max_rate",
        "input_chat",
        "created_at",
    ]

    readonly_fields = fields

    inlines = [
        OutputChatMessageInline,
        TextAnswerInline,
    ]

    ordering = ["-created_at"]
