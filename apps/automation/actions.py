"""Action registry for workflow steps.

Each action is `fn(config: dict, context: dict, run) -> dict`. The returned dict
is merged into the shared context and made available to later steps. Register
new actions with the @action decorator — this is the platform's AI-automation
extension point (browser automation, email, Slack, etc. plug in here).
"""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger("neuraforge")

ACTIONS: dict[str, Callable] = {}


def action(name: str):
    def decorator(fn: Callable) -> Callable:
        ACTIONS[name] = fn
        return fn

    return decorator


def _interpolate(value, context: dict):
    """Replace {{key}} references in strings with values from context."""
    if isinstance(value, str):
        for k, v in context.items():
            value = value.replace(f"{{{{{k}}}}}", str(v))
    return value


# --------------------------------------------------------------------------
# Built-in actions
# --------------------------------------------------------------------------
@action("ai.summarize")
def summarize_action(config, context, run) -> dict:
    from apps.ai_engine.services.summarization import SummarizationService

    text = _interpolate(config.get("text", context.get("text", "")), context)
    summary = SummarizationService().summarize(text, mode=config.get("mode", "long"))
    return {"summary": summary}


@action("ai.rag_query")
def rag_query_action(config, context, run) -> dict:
    from apps.ai_engine.services.rag import RAGService

    question = _interpolate(config.get("question", ""), context)
    result = RAGService().answer(question, owner_id=run.workflow.owner_id)
    return {"answer": result.answer, "citations": result.citations}


@action("ai.run_agents")
def run_agents_action(config, context, run) -> dict:
    from apps.ai_engine.services.agents import research_team

    task = _interpolate(config.get("task", ""), context)
    ctx = research_team().run(task, owner_id=str(run.workflow.owner_id))
    return {"report": ctx.scratchpad[-1]["output"] if ctx.scratchpad else ""}


@action("notes.create")
def create_note_action(config, context, run) -> dict:
    from apps.notes.models import Note
    from apps.notes.tasks import enrich_note

    note = Note.objects.create(
        owner_id=run.workflow.owner_id,
        team_id=run.workflow.team_id,
        title=_interpolate(config.get("title", "Automated note"), context),
        content=_interpolate(config.get("content", context.get("summary", "")), context),
    )
    enrich_note.delay(str(note.id))
    return {"note_id": str(note.id)}


@action("webhook.send")
def send_webhook_action(config, context, run) -> dict:
    """POST the current context to an external URL (Zapier-style outbound)."""
    import json
    import urllib.request

    url = config["url"]
    payload = json.dumps({"context": context, "payload": config.get("body", {})}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return {"webhook_status": resp.status}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Webhook to %s failed: %s", url, exc)
        return {"webhook_status": "error", "webhook_error": str(exc)}


def get_action(name: str) -> Callable:
    if name not in ACTIONS:
        raise KeyError(f"Unknown action '{name}'. Registered: {sorted(ACTIONS)}")
    return ACTIONS[name]
