"""Zapier-style workflow automation.

A Workflow has a trigger (manual / schedule / event / webhook) and an ordered
list of Steps. Each Step runs a registered Action, threading a shared context
dict from one step to the next. Every execution is recorded as a WorkflowRun.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, OwnedModel


class Workflow(BaseModel, OwnedModel):
    class Trigger(models.TextChoices):
        MANUAL = "manual", _("Manual")
        SCHEDULE = "schedule", _("Schedule (cron)")
        EVENT = "event", _("Platform event")
        WEBHOOK = "webhook", _("Inbound webhook")

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    trigger_type = models.CharField(
        max_length=12, choices=Trigger.choices, default=Trigger.MANUAL
    )
    # For SCHEDULE: {"cron": "0 9 * * *"}; EVENT: {"event": "document.indexed"};
    # WEBHOOK: {"secret": "..."}.
    trigger_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["trigger_type", "is_active"])]

    def __str__(self) -> str:
        return self.name


class WorkflowStep(BaseModel):
    """A single ordered action within a workflow."""

    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name="steps"
    )
    order = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=160, blank=True)
    # Key into the action registry (apps.automation.actions.ACTIONS).
    action_type = models.CharField(max_length=64)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("workflow", "order")

    def __str__(self) -> str:
        return f"{self.workflow.name}[{self.order}] {self.action_type}"


class WorkflowRun(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        RUNNING = "running", _("Running")
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")

    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name="runs"
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    trigger_payload = models.JSONField(default=dict, blank=True)
    context = models.JSONField(default=dict, blank=True)  # final shared context
    step_results = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Run<{self.workflow.name}:{self.status}>"
