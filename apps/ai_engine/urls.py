from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AIAssistantViewSet,
    ChatView,
    ConversationViewSet,
    SummarizeView,
    run_agents,
)

router = DefaultRouter()
router.register("assistants", AIAssistantViewSet, basename="assistant")
router.register("conversations", ConversationViewSet, basename="conversation")

urlpatterns = [
    path("chat/", ChatView.as_view(), name="ai-chat"),
    path("summarize/", SummarizeView.as_view(), name="ai-summarize"),
    path("agents/run/", run_agents, name="ai-agents-run"),
    *router.urls,
]
