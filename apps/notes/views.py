from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Note, NoteLink, Tag
from .serializers import NoteLinkSerializer, NoteSerializer, TagSerializer
from .tasks import enrich_note


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    filterset_fields = ["is_pinned", "tags"]
    search_fields = ["title", "content"]
    ordering_fields = ["created_at", "updated_at", "title"]

    def get_queryset(self):
        return (
            Note.objects.filter(owner=self.request.user)
            .prefetch_related("tags", "outgoing_links")
        )

    def perform_create(self, serializer):
        note = serializer.save(owner=self.request.user)
        enrich_note.delay(str(note.id))

    def perform_update(self, serializer):
        note = serializer.save()
        enrich_note.delay(str(note.id))

    @action(detail=True, methods=["post"])
    def link(self, request, pk=None):
        """POST /notes/{id}/link {target, label} — create a knowledge-graph edge."""
        note = self.get_object()
        target_id = request.data.get("target")
        target = Note.objects.filter(id=target_id, owner=request.user).first()
        if not target:
            return Response({"detail": "Target note not found."}, status=404)
        link, _ = NoteLink.objects.get_or_create(
            source=note, target=target, defaults={"label": request.data.get("label", "")}
        )
        return Response(NoteLinkSerializer(link).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def backlinks(self, request, pk=None):
        """GET /notes/{id}/backlinks — notes that link TO this note."""
        note = self.get_object()
        links = note.incoming_links.select_related("source")
        return Response(
            [{"source": str(l.source_id), "title": l.source.title, "label": l.label} for l in links]
        )
