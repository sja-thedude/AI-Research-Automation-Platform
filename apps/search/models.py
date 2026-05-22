"""Search history (analytics + 'recent searches' UX)."""
from django.db import models

from apps.core.models import BaseModel, OwnedModel


class SearchQuery(BaseModel, OwnedModel):
    class Mode(models.TextChoices):
        SEMANTIC = "semantic", "Semantic"
        FULLTEXT = "fulltext", "Full-text"
        HYBRID = "hybrid", "Hybrid"

    text = models.CharField(max_length=500)
    mode = models.CharField(max_length=12, choices=Mode.choices, default=Mode.HYBRID)
    result_count = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Search queries"

    def __str__(self) -> str:
        return f"{self.text} ({self.mode})"
