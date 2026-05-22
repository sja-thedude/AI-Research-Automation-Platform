from django.contrib import admin

from .models import AIAssistant, Conversation, KnowledgeChunk, Message


@admin.register(AIAssistant)
class AIAssistantAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "model", "is_public", "created_at")
    list_filter = ("is_public",)
    search_fields = ("name", "description")


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "content", "model", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "owner", "assistant", "created_at")
    inlines = [MessageInline]


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("__str__", "owner", "chunk_index", "token_count", "created_at")
    search_fields = ("content",)
    readonly_fields = ("embedding",)
