from django.contrib import admin

from .models import Workflow, WorkflowRun, WorkflowStep


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 1


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "trigger_type", "is_active", "owner", "created_at")
    list_filter = ("trigger_type", "is_active")
    search_fields = ("name",)
    inlines = [WorkflowStepInline]


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = ("workflow", "status", "started_at", "finished_at")
    list_filter = ("status",)
    readonly_fields = ("context", "step_results", "trigger_payload")
