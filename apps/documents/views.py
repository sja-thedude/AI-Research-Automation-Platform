from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.core.permissions import IsOwnerOrTeamMember

from .models import Document, Folder
from .serializers import DocumentSerializer, FolderSerializer
from .tasks import process_document, summarize_document


class FolderViewSet(viewsets.ModelViewSet):
    serializer_class = FolderSerializer

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DocumentViewSet(viewsets.ModelViewSet):
    """Upload + manage documents. Upload kicks off async ingestion."""

    serializer_class = DocumentSerializer
    permission_classes = [*viewsets.ModelViewSet.permission_classes, IsOwnerOrTeamMember]
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["file_type", "status", "folder"]
    search_fields = ["title", "extracted_text"]
    ordering_fields = ["created_at", "title", "size_bytes"]

    def get_queryset(self):
        user = self.request.user
        # Documents the user owns OR that belong to a team they're a member of.
        return Document.objects.filter(
            Q(owner=user) | Q(team__memberships__user=user)
        ).distinct()

    def perform_create(self, serializer):
        doc = serializer.save(owner=self.request.user)
        # Fire-and-forget ingestion; client polls status or listens via WS.
        process_document.delay(str(doc.id))

    @action(detail=True, methods=["post"])
    def reprocess(self, request, pk=None):
        """Re-run extraction + indexing (e.g. after an extractor upgrade)."""
        doc = self.get_object()
        process_document.delay(str(doc.id))
        return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def summarize(self, request, pk=None):
        """Queue an AI summary of the document."""
        doc = self.get_object()
        summarize_document.delay(str(doc.id))
        return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)
