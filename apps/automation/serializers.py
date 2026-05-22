from rest_framework import serializers

from .actions import ACTIONS
from .models import Workflow, WorkflowRun, WorkflowStep


class WorkflowStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStep
        fields = ("id", "order", "name", "action_type", "config")
        read_only_fields = ("id",)

    def validate_action_type(self, value):
        if value not in ACTIONS:
            raise serializers.ValidationError(
                f"Unknown action. Available: {sorted(ACTIONS)}"
            )
        return value


class WorkflowSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, required=False)

    class Meta:
        model = Workflow
        fields = (
            "id",
            "name",
            "description",
            "trigger_type",
            "trigger_config",
            "is_active",
            "steps",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        steps = validated_data.pop("steps", [])
        workflow = Workflow.objects.create(**validated_data)
        for step in steps:
            WorkflowStep.objects.create(workflow=workflow, **step)
        return workflow

    def update(self, instance, validated_data):
        steps = validated_data.pop("steps", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if steps is not None:
            instance.steps.all().delete()
            for step in steps:
                WorkflowStep.objects.create(workflow=instance, **step)
        return instance


class WorkflowRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowRun
        fields = (
            "id",
            "workflow",
            "status",
            "trigger_payload",
            "context",
            "step_results",
            "error",
            "started_at",
            "finished_at",
            "created_at",
        )
        read_only_fields = fields
