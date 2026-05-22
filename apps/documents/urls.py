from rest_framework.routers import DefaultRouter

from .views import DocumentViewSet, FolderViewSet

router = DefaultRouter()
router.register("folders", FolderViewSet, basename="folder")
router.register("", DocumentViewSet, basename="document")

urlpatterns = router.urls
