from rest_framework import serializers

from .models import Note, NoteLink, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "color")
        read_only_fields = ("id",)


class NoteLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteLink
        fields = ("id", "source", "target", "label", "created_at")
        read_only_fields = ("id", "created_at")


class NoteSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, write_only=True, required=False, source="tags"
    )
    outgoing = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = (
            "id",
            "title",
            "content",
            "tags",
            "tag_ids",
            "source_document",
            "is_pinned",
            "ai_metadata",
            "outgoing",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "ai_metadata", "created_at", "updated_at")

    def get_outgoing(self, obj) -> list:
        return [
            {"target": str(link.target_id), "label": link.label}
            for link in obj.outgoing_links.all()
        ]
