"""Knowledge graph: entities and the relationships between them.

Entities + Relationships form a property graph extracted from the user's
documents and notes (via LLM entity/relation extraction). This powers
graph-aware retrieval and visualization in the research dashboard.
"""
from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel, OwnedModel


class Entity(BaseModel, OwnedModel):
    class Kind(models.TextChoices):
        PERSON = "person", "Person"
        ORG = "org", "Organization"
        CONCEPT = "concept", "Concept"
        PLACE = "place", "Place"
        EVENT = "event", "Event"
        PRODUCT = "product", "Product"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.CONCEPT)
    aliases = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    # Optional provenance: which sources mention this entity.
    source_ids = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "Entities"
        unique_together = ("owner", "name", "kind")
        indexes = [models.Index(fields=["owner", "kind"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.kind})"


class Relationship(BaseModel, OwnedModel):
    """A directed, typed edge: (subject) --predicate--> (object)."""

    subject = models.ForeignKey(
        Entity, on_delete=models.CASCADE, related_name="relations_out"
    )
    predicate = models.CharField(max_length=120)  # "works_at", "related_to"…
    obj = models.ForeignKey(
        Entity, on_delete=models.CASCADE, related_name="relations_in"
    )
    weight = models.FloatField(default=1.0)
    source_ids = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ("subject", "predicate", "obj")
        indexes = [models.Index(fields=["predicate"])]

    def __str__(self) -> str:
        return f"{self.subject.name} -{self.predicate}-> {self.obj.name}"
