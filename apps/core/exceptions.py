"""Centralized API exception handling -> consistent JSON error envelopes."""
from __future__ import annotations

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("neuraforge")


class AIServiceError(Exception):
    """Raised when an upstream AI/LLM provider fails irrecoverably."""


class VectorStoreError(Exception):
    """Raised on vector backend failures (pgvector/chroma/pinecone)."""


class DocumentProcessingError(Exception):
    """Raised when a document cannot be parsed/extracted."""


def api_exception_handler(exc, context):
    """Wrap DRF's handler so every error response has a stable shape:

        {"error": {"type": "...", "detail": ..., "status": 4xx}}
    """
    response = drf_exception_handler(exc, context)
    view = context.get("view")
    if response is None:
        # Unhandled exception — log with traceback, return opaque 500.
        logger.exception("Unhandled error in %s", view, exc_info=exc)
        return Response(
            {"error": {"type": "server_error", "detail": "Internal server error.", "status": 500}},
            status=500,
        )

    response.data = {
        "error": {
            "type": exc.__class__.__name__,
            "detail": response.data,
            "status": response.status_code,
        }
    }
    return response
