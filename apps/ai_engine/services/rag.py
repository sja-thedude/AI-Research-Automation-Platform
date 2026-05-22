"""Retrieval-Augmented Generation pipeline.

    question -> retrieve(top_k) -> build grounded prompt -> LLM -> answer+citations

Exposes both a blocking `answer()` and a token `stream()` generator for
WebSocket / SSE delivery.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterator

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import get_chat_model
from .retrieval import retrieve

logger = logging.getLogger("neuraforge")

SYSTEM_PROMPT = (
    "You are NeuraForge AI, a precise research assistant. Answer the user's "
    "question using ONLY the provided context. Cite sources inline using "
    "bracketed numbers like [1], [2] that map to the context blocks. If the "
    "context is insufficient, say so plainly and do not fabricate. Be concise "
    "and well-structured."
)


@dataclass
class RAGResult:
    answer: str
    citations: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    model: str = ""


def _build_context(chunks) -> tuple[str, list[dict]]:
    """Render retrieved chunks into a numbered context block + citation list."""
    blocks, citations = [], []
    for i, c in enumerate(chunks, start=1):
        blocks.append(f"[{i}] (source: {c.source_type}) {c.content}")
        citations.append(
            {
                "ref": i,
                "chunk_id": c.chunk_id,
                "source_type": c.source_type,
                "source_id": c.source_id,
                "score": c.score,
                "snippet": c.content[:240],
            }
        )
    return "\n\n".join(blocks), citations


def _messages(question: str, context: str, system_prompt: str, history=None):
    msgs = [SystemMessage(content=system_prompt)]
    for turn in history or []:
        # history: list of {"role": "user"|"assistant", "content": str}
        cls = HumanMessage if turn["role"] == "user" else SystemMessage
        msgs.append(cls(content=turn["content"]))
    user = (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer with inline [n] citations."
    )
    msgs.append(HumanMessage(content=user))
    return msgs


class RAGService:
    def __init__(self, *, model: str | None = None, temperature: float | None = None,
                 system_prompt: str = SYSTEM_PROMPT):
        self.model_name = model
        self.temperature = temperature
        self.system_prompt = system_prompt

    def _retrieve(self, question, owner_id, team_id, source_ids, top_k):
        chunks = retrieve(
            question,
            owner_id=owner_id,
            team_id=team_id,
            source_ids=source_ids,
            top_k=top_k,
        )
        return _build_context(chunks)

    def answer(
        self,
        question: str,
        *,
        owner_id=None,
        team_id=None,
        source_ids=None,
        top_k=None,
        history=None,
    ) -> RAGResult:
        context, citations = self._retrieve(question, owner_id, team_id, source_ids, top_k)
        llm = get_chat_model(self.model_name, self.temperature)
        response = llm.invoke(_messages(question, context, self.system_prompt, history))
        usage = getattr(response, "response_metadata", {}).get("token_usage", {})
        return RAGResult(
            answer=response.content,
            citations=citations,
            usage=usage,
            model=getattr(response, "response_metadata", {}).get("model_name", ""),
        )

    def stream(
        self,
        question: str,
        *,
        owner_id=None,
        team_id=None,
        source_ids=None,
        top_k=None,
        history=None,
    ) -> Iterator[dict]:
        """Yield {'type': 'citations'|'token'|'done', ...} events for streaming."""
        context, citations = self._retrieve(question, owner_id, team_id, source_ids, top_k)
        yield {"type": "citations", "citations": citations}

        llm = get_chat_model(self.model_name, self.temperature)
        buffer = []
        for chunk in llm.stream(_messages(question, context, self.system_prompt, history)):
            token = chunk.content or ""
            if token:
                buffer.append(token)
                yield {"type": "token", "token": token}
        yield {"type": "done", "answer": "".join(buffer), "citations": citations}
