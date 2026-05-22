from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Entity, Relationship
from .serializers import EntitySerializer, RelationshipSerializer


class EntityViewSet(viewsets.ModelViewSet):
    serializer_class = EntitySerializer
    filterset_fields = ["kind"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return Entity.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"])
    def neighbors(self, request, pk=None):
        """GET /knowledge/entities/{id}/neighbors — 1-hop subgraph."""
        entity = self.get_object()
        out = entity.relations_out.select_related("obj")
        inc = entity.relations_in.select_related("subject")
        return Response(
            {
                "entity": EntitySerializer(entity).data,
                "outgoing": RelationshipSerializer(out, many=True).data,
                "incoming": RelationshipSerializer(inc, many=True).data,
            }
        )


class RelationshipViewSet(viewsets.ModelViewSet):
    serializer_class = RelationshipSerializer
    filterset_fields = ["predicate", "subject", "obj"]

    def get_queryset(self):
        return Relationship.objects.filter(owner=self.request.user).select_related(
            "subject", "obj"
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class GraphView(viewsets.ViewSet):
    """GET /knowledge/graph — nodes + edges for visualization (D3/Cytoscape)."""

    def list(self, request):
        entities = Entity.objects.filter(owner=request.user)
        rels = Relationship.objects.filter(owner=request.user).select_related(
            "subject", "obj"
        )
        nodes = [
            {"id": str(e.id), "label": e.name, "kind": e.kind} for e in entities
        ]
        edges = [
            {
                "source": str(r.subject_id),
                "target": str(r.obj_id),
                "label": r.predicate,
                "weight": r.weight,
            }
            for r in rels
        ]
        return Response({"nodes": nodes, "edges": edges})
