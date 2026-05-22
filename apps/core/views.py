"""Operational endpoints (health/readiness) used by load balancers & k8s."""
from django.db import connection
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Liveness + dependency readiness probe.

    Returns 200 only when DB and Redis are reachable, so orchestrators can
    gate traffic on a genuinely-ready instance.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        checks = {"database": self._check_db(), "cache": self._check_cache()}
        healthy = all(checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=200 if healthy else 503,
        )

    @staticmethod
    def _check_db() -> bool:
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    @staticmethod
    def _check_cache() -> bool:
        try:
            cache.set("healthcheck", "1", 5)
            return cache.get("healthcheck") == "1"
        except Exception:
            return False
