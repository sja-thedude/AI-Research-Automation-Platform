from rest_framework.routers import DefaultRouter

from .views import WorkflowRunViewSet, WorkflowViewSet

router = DefaultRouter()
router.register("workflows", WorkflowViewSet, basename="workflow")
router.register("runs", WorkflowRunViewSet, basename="workflow-run")

urlpatterns = router.urls
