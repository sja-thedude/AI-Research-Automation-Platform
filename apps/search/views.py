import time

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SearchQuery as SearchQueryLog
from .services import SEARCHERS, to_dicts


class SearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField()
    mode = serializers.ChoiceField(
        choices=["semantic", "fulltext", "hybrid"], default="hybrid"
    )
    top_k = serializers.IntegerField(default=10, min_value=1, max_value=50)
    team_id = serializers.UUIDField(required=False)


class SearchView(APIView):
    """GET/POST /search — unified semantic/full-text/hybrid search."""

    def get(self, request):
        return self._run(request, request.query_params)

    def post(self, request):
        return self._run(request, request.data)

    def _run(self, request, payload):
        ser = SearchRequestSerializer(data=payload)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        started = time.perf_counter()
        searcher = SEARCHERS[d["mode"]]
        hits = searcher(
            d["q"],
            owner_id=request.user.id,
            team_id=d.get("team_id"),
            top_k=d["top_k"],
        )
        duration_ms = int((time.perf_counter() - started) * 1000)

        SearchQueryLog.objects.create(
            owner=request.user,
            text=d["q"][:500],
            mode=d["mode"],
            result_count=len(hits),
            duration_ms=duration_ms,
        )
        return Response(
            {
                "query": d["q"],
                "mode": d["mode"],
                "count": len(hits),
                "duration_ms": duration_ms,
                "results": to_dicts(hits),
            }
        )
