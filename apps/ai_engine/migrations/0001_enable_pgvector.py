"""Enable the pgvector extension before any VectorField tables are created.

Hand-written so it always runs first. `makemigrations` will generate the
model migration (0002_*) which Django auto-chains after this one, ensuring the
`vector` type exists when `KnowledgeChunk.embedding` is created.
"""
from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    initial = True
    dependencies: list = []
    operations = [VectorExtension()]
