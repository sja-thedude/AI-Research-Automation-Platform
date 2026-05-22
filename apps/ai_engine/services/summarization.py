"""Summarization + insight generation.

Short inputs are summarized in one shot; long inputs use a map-reduce strategy
(summarize chunks, then summarize the summaries) so we stay within context
limits for research-length documents.
"""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .llm import get_chat_model

logger = logging.getLogger("neuraforge")

MODE_PROMPTS = {
    "short": "Summarize the text in 2-3 sentences.",
    "long": "Write a structured summary with headings and bullet points covering all key ideas.",
    "research": (
        "Produce a research-grade summary: objective, key findings, methodology "
        "(if present), and conclusions. Preserve technical accuracy."
    ),
    "insights": (
        "Extract the most important insights, implications and open questions as "
        "a concise bulleted list."
    ),
}

# Above this length we map-reduce instead of single-shotting.
MAP_REDUCE_THRESHOLD = 12000


class SummarizationService:
    def __init__(self, model: str | None = None):
        self.llm = get_chat_model(model, temperature=0.3)

    def _one_shot(self, text: str, instruction: str, title: str = "") -> str:
        prefix = f"Title: {title}\n\n" if title else ""
        resp = self.llm.invoke(
            [
                SystemMessage(content="You are an expert research summarizer."),
                HumanMessage(content=f"{instruction}\n\n{prefix}{text}"),
            ]
        )
        return resp.content.strip()

    def summarize(self, text: str, *, mode: str = "long", title: str = "") -> str:
        text = (text or "").strip()
        if not text:
            return ""
        instruction = MODE_PROMPTS.get(mode, MODE_PROMPTS["long"])

        if len(text) <= MAP_REDUCE_THRESHOLD:
            return self._one_shot(text, instruction, title)

        # Map: summarize each chunk; Reduce: summarize the partials.
        splitter = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=200)
        partials = [
            self._one_shot(chunk, "Summarize this section concisely.")
            for chunk in splitter.split_text(text)
        ]
        combined = "\n\n".join(partials)
        return self._one_shot(combined, instruction, title)

    def insights(self, text: str, title: str = "") -> str:
        return self.summarize(text, mode="insights", title=title)
