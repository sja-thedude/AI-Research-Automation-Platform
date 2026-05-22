from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AIAssistant, Conversation, Message
from .serializers import (
    AgentRunRequestSerializer,
    AIAssistantSerializer,
    ChatRequestSerializer,
    ConversationSerializer,
    SummarizeRequestSerializer,
)
from .services.rag import RAGService
from .services.summarization import SummarizationService
from .tasks import run_agent_pipeline


class AIAssistantViewSet(viewsets.ModelViewSet):
    """Build & manage 'trainable' AI assistants."""

    serializer_class = AIAssistantSerializer

    def get_queryset(self):
        from django.db.models import Q

        return AIAssistant.objects.filter(
            Q(owner=self.request.user) | Q(is_public=True)
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(owner=self.request.user).prefetch_related(
            "messages"
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ChatView(APIView):
    """POST /ai/chat — synchronous RAG answer with citations.

    Persists the turn into a Conversation. For token streaming use the
    WebSocket endpoint (apps.chat) instead.
    """

    def post(self, request):
        ser = ChatRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        user = request.user

        conversation = self._get_or_create_conversation(data, user)
        assistant = conversation.assistant

        # Persist the user's message.
        Message.objects.create(
            conversation=conversation, role=Message.Role.USER, content=data["question"]
        )
        history = list(
            conversation.messages.order_by("created_at").values("role", "content")
        )[-10:]

        rag = RAGService(
            model=assistant.resolved_model if assistant else None,
            temperature=assistant.temperature if assistant else None,
            system_prompt=(assistant.system_prompt if assistant and assistant.system_prompt
                           else RAGService().system_prompt),
        )
        result = rag.answer(
            data["question"],
            owner_id=user.id,
            source_ids=[str(s) for s in data.get("source_ids", [])] or None,
            top_k=data.get("top_k"),
            history=history,
        )

        msg = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=result.answer,
            citations=result.citations,
            token_usage=result.usage,
            model=result.model,
        )
        return Response(
            {
                "conversation_id": str(conversation.id),
                "answer": result.answer,
                "citations": result.citations,
                "message_id": str(msg.id),
            }
        )

    def _get_or_create_conversation(self, data, user) -> Conversation:
        if data.get("conversation_id"):
            return Conversation.objects.get(id=data["conversation_id"], owner=user)
        assistant = None
        if data.get("assistant_id"):
            assistant = AIAssistant.objects.filter(id=data["assistant_id"]).first()
        return Conversation.objects.create(
            owner=user,
            assistant=assistant,
            title=data["question"][:80],
        )


class SummarizeView(APIView):
    """POST /ai/summarize — summarize arbitrary text / generate insights."""

    def post(self, request):
        ser = SummarizeRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        summary = SummarizationService().summarize(
            d["text"], mode=d["mode"], title=d.get("title", "")
        )
        return Response({"summary": summary, "mode": d["mode"]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_agents(request):
    """POST /ai/agents/run — kick off the multi-agent research pipeline (async)."""
    ser = AgentRunRequestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    task = run_agent_pipeline.delay(
        ser.validated_data["task"],
        owner_id=str(request.user.id),
        team_id=str(ser.validated_data.get("team_id")) if ser.validated_data.get("team_id") else None,
    )
    return Response({"task_id": task.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)
