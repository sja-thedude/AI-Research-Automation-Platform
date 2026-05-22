from rest_framework.routers import DefaultRouter

from .views import EntityViewSet, GraphView, RelationshipViewSet

router = DefaultRouter()
router.register("entities", EntityViewSet, basename="entity")
router.register("relationships", RelationshipViewSet, basename="relationship")
router.register("graph", GraphView, basename="graph")

urlpatterns = router.urls
