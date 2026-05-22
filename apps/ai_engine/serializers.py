from rest_framework import serializers

from .models import AIAssistant, Conversation, Message


class AIAssistantSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAssistant
        fields = (
            "id",
            "name",
            "description",
            "system_prompt",
            "model",
            "temperature",
            "tools",
            "knowledge_scope",
            "is_public",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "citations", "token_usage", "model", "created_at")
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.IntegerField(source="messages.count", read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "title",
            "assistant",
            "metadata",
            "message_count",
            "messages",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "messages", "message_count")


class ChatRequestSerializer(serializers.Serializer):
    """Body for POST /ai/chat — single-turn RAG question."""

    question = serializers.CharField()
    conversation_id = serializers.UUIDField(required=False)
    assistant_id = serializers.UUIDField(required=False)
    source_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20)


class SummarizeRequestSerializer(serializers.Serializer):
    text = serializers.CharField()
    mode = serializers.ChoiceField(
        choices=["short", "long", "research", "insights"], default="long"
    )
    title = serializers.CharField(required=False, allow_blank=True, default="")


class AgentRunRequestSerializer(serializers.Serializer):
    task = serializers.CharField()
    team_id = serializers.UUIDField(required=False)
