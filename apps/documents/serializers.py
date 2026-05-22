from django.conf import settings
from rest_framework import serializers

from .extractors import detect_file_type
from .models import Document, Folder


class FolderSerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(source="documents.count", read_only=True)

    class Meta:
        model = Folder
        fields = ("id", "name", "parent", "document_count", "created_at")
        read_only_fields = ("id", "created_at")


class DocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "title",
            "file",
            "download_url",
            "folder",
            "file_type",
            "mime_type",
            "size_bytes",
            "status",
            "error",
            "page_count",
            "word_count",
            "language",
            "summary",
            "metadata",
            "created_at",
        )
        read_only_fields = (
            "id",
            "file_type",
            "mime_type",
            "size_bytes",
            "status",
            "error",
            "page_count",
            "word_count",
            "language",
            "summary",
            "metadata",
            "created_at",
        )
        extra_kwargs = {"file": {"write_only": True}}

    def get_download_url(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    def validate_file(self, value):
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit."
            )
        return value

    def create(self, validated_data):
        upload = validated_data["file"]
        validated_data.setdefault("title", upload.name)
        validated_data["file_type"] = detect_file_type(
            upload.name, getattr(upload, "content_type", "")
        )
        validated_data["mime_type"] = getattr(upload, "content_type", "")
        validated_data["size_bytes"] = upload.size
        return super().create(validated_data)
