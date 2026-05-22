"""Automation async tasks + event dispatch."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("neuraforge")


@shared_task
def execute_workflow(workflow_id: str, trigger_payload: dict | None = None) -> dict:
    """Create a WorkflowRun and execute it synchronously inside the task."""
    from .engine import execute_run
    from .models import Workflow, WorkflowRun

    workflow = Workflow.objects.get(id=workflow_id)
    if not workflow.is_active:
        return {"status": "skipped", "reason": "inactive"}

    run = WorkflowRun.objects.create(
        workflow=workflow, trigger_payload=trigger_payload or {}
    )
    run = execute_run(run)
    return {"run_id": str(run.id), "status": run.status}


@shared_task
def dispatch_event(event: str, payload: dict | None = None, owner_id: str | None = None):
    """Fan out a platform event to every active EVENT-triggered workflow.

    Call from signals, e.g. when a document finishes indexing:
        dispatch_event.delay("document.indexed", {...}, owner_id=...)
    """
    from .models import Workflow

    qs = Workflow.objects.filter(
        trigger_type=Workflow.Trigger.EVENT,
        is_active=True,
        trigger_config__event=event,
    )
    if owner_id:
        qs = qs.filter(owner_id=owner_id)

    fired = 0
    for wf in qs:
        execute_workflow.delay(str(wf.id), trigger_payload=payload or {})
        fired += 1
    return {"event": event, "workflows_fired": fired}
