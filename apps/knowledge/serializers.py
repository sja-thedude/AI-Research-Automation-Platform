from rest_framework import serializers

from .models import Entity, Relationship


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = (
            "id",
            "name",
            "kind",
            "aliases",
            "description",
            "source_ids",
            "metadata",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class RelationshipSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    obj_name = serializers.CharField(source="obj.name", read_only=True)

    class Meta:
        model = Relationship
        fields = (
            "id",
            "subject",
            "subject_name",
            "predicate",
            "obj",
            "obj_name",
            "weight",
            "source_ids",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
