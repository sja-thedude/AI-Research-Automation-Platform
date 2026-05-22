"""WebSocket consumers.

* ChatConsumer — streams RAG answers token-by-token (ChatGPT-style typing) and
  persists the turn into the conversation.
* NotificationConsumer — per-user push channel for async events (e.g. a
  document finished indexing). Tasks broadcast to group "user_<id>".
"""
from __future__ import annotations

import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    """ws://…/ws/chat/<conversation_id>/?token=<jwt>

    Inbound:  {"question": "...", "source_ids": [...], "top_k": 6}
    Outbound: {"type": "citations"|"token"|"done"|"error", ...}
    """

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)  # unauthorized
            return
        self.conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self._send({"type": "error", "detail": "Invalid JSON"})
            return

        question = (payload.get("question") or "").strip()
        if not question:
            await self._send({"type": "error", "detail": "Empty question"})
            return

        conversation = await self._get_or_create_conversation()
        await self._save_message(conversation, "user", question)
        history = await self._history(conversation)

        from apps.ai_engine.services.rag import RAGService

        rag = RAGService()
        answer_parts, citations = [], []

        # RAGService.stream is a sync generator; iterate it off the event loop.
        events = await sync_to_async(list)(
            rag.stream(
                question,
                owner_id=self.user.id,
                source_ids=[str(s) for s in payload.get("source_ids", [])] or None,
                top_k=payload.get("top_k"),
                history=history,
            )
        )
        for event in events:
            if event["type"] == "citations":
                citations = event["citations"]
            elif event["type"] == "token":
                answer_parts.append(event["token"])
            await self._send(event)

        await self._save_message(
            conversation, "assistant", "".join(answer_parts), citations=citations
        )

    async def _send(self, data: dict):
        await self.send(text_data=json.dumps(data))

    # ---- DB helpers (sync ORM wrapped) ----
    @sync_to_async
    def _get_or_create_conversation(self):
        from apps.ai_engine.models import Conversation

        if self.conversation_id and self.conversation_id != "new":
            return Conversation.objects.get(id=self.conversation_id, owner=self.user)
        return Conversation.objects.create(owner=self.user, title="New chat")

    @sync_to_async
    def _save_message(self, conversation, role, content, citations=None):
        from apps.ai_engine.models import Message

        return Message.objects.create(
            conversation=conversation,
            role=role,
            content=content,
            citations=citations or [],
        )

    @sync_to_async
    def _history(self, conversation):
        from apps.ai_engine.models import Message

        return list(
            Message.objects.filter(conversation=conversation)
            .order_by("created_at")
            .values("role", "content")
        )[-10:]


class NotificationConsumer(AsyncWebsocketConsumer):
    """ws://…/ws/notifications/?token=<jwt> — per-user event push."""

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group = f"user_{user.id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notify(self, event):
        """Handler for messages sent via group_send(type="notify")."""
        await self.send(
            text_data=json.dumps({"event": event["event"], "data": event["data"]})
        )
