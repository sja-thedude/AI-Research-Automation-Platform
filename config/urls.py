"""Root URL configuration for NeuraForge AI.

API is versioned under /api/v1/. Each app exposes a router-based urls module.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import HealthCheckView

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("documents/", include("apps.documents.urls")),
    path("ai/", include("apps.ai_engine.urls")),
    path("search/", include("apps.search.urls")),
    path("notes/", include("apps.notes.urls")),
    path("automation/", include("apps.automation.urls")),
    path("knowledge/", include("apps.knowledge.urls")),
    path("chat/", include("apps.chat.urls")),
]

urlpatterns = [
    # Land browsers on the interactive API docs instead of a bare 404.
    path("", RedirectView.as_view(url="/api/docs/", permanent=False), name="root"),
    path("admin/", admin.site.urls),
    path("health/", HealthCheckView.as_view(), name="health"),
    # API
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
    # OpenAPI schema + docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar

        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    except ImportError:
        pass
