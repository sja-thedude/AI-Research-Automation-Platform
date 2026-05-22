from rest_framework.routers import DefaultRouter

from .views import NoteViewSet, TagViewSet

router = DefaultRouter()
router.register("tags", TagViewSet, basename="tag")
router.register("", NoteViewSet, basename="note")

urlpatterns = router.urls
