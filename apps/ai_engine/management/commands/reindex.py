"""Re-embed all indexed documents and notes into the vector store.

Useful after changing the embedding model/dimension or chunking strategy:

    python manage.py reindex --type all
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Rebuild vector embeddings for documents and/or notes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=["documents", "notes", "all"],
            default="all",
        )

    def handle(self, *args, **opts):
        from apps.ai_engine.services.ingestion import ingest_source

        target = opts["type"]
        count = 0

        if target in ("documents", "all"):
            from apps.documents.models import Document

            for doc in Document.objects.exclude(extracted_text=""):
                ingest_source(doc, doc.extracted_text, extra_metadata={"title": doc.title})
                count += 1
                self.stdout.write(f"  reindexed document {doc.id}")

        if target in ("notes", "all"):
            from apps.notes.models import Note

            for note in Note.objects.all():
                ingest_source(note, f"{note.title}\n\n{note.content}", extra_metadata={"title": note.title})
                count += 1
                self.stdout.write(f"  reindexed note {note.id}")

        self.stdout.write(self.style.SUCCESS(f"Reindexed {count} source(s)."))
