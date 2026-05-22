from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .actions import ACTIONS
from .models import Workflow, WorkflowRun
from .serializers import WorkflowRunSerializer, WorkflowSerializer
from .tasks import execute_workflow


class WorkflowViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowSerializer
    filterset_fields = ["trigger_type", "is_active"]

    def get_queryset(self):
        return Workflow.objects.filter(owner=self.request.user).prefetch_related("steps")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        """POST /automation/workflows/{id}/run — trigger manually (async)."""
        workflow = self.get_object()
        task = execute_workflow.delay(str(workflow.id), trigger_payload=request.data or {})
        return Response(
            {"task_id": task.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=["get"])
    def runs(self, request, pk=None):
        """GET /automation/workflows/{id}/runs — execution history."""
        workflow = self.get_object()
        qs = workflow.runs.all()[:50]
        return Response(WorkflowRunSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def actions(self, request):
        """GET /automation/workflows/actions — list registered action types."""
        return Response({"actions": sorted(ACTIONS.keys())})


class WorkflowRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkflowRunSerializer
    filterset_fields = ["status", "workflow"]

    def get_queryset(self):
        return WorkflowRun.objects.filter(workflow__owner=self.request.user)
