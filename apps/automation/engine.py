"""Workflow execution engine — runs a workflow's steps in order."""
from __future__ import annotations

import logging

from django.utils import timezone

from .actions import get_action
from .models import WorkflowRun

logger = logging.getLogger("neuraforge")


def execute_run(run: WorkflowRun) -> WorkflowRun:
    """Run every step of `run.workflow`, threading a shared context.

    Each step's output is merged into the context. Any step exception fails the
    run but preserves the results gathered so far for debugging.
    """
    run.status = WorkflowRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])

    context: dict = dict(run.trigger_payload or {})
    results: list[dict] = []

    try:
        for step in run.workflow.steps.all():
            logger.info("Run %s: step %s (%s)", run.id, step.order, step.action_type)
            handler = get_action(step.action_type)
            output = handler(step.config, context, run) or {}
            context.update(output)
            results.append(
                {"order": step.order, "action": step.action_type, "output": output}
            )
        run.status = WorkflowRun.Status.SUCCESS
    except Exception as exc:  # noqa: BLE001
        logger.exception("Workflow run %s failed", run.id)
        run.status = WorkflowRun.Status.FAILED
        run.error = str(exc)
    finally:
        run.context = context
        run.step_results = results
        run.finished_at = timezone.now()
        run.save()

    return run
