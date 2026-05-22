from django.urls import path

from .views import WebSocketInfoView

urlpatterns = [
    path("", WebSocketInfoView.as_view(), name="ws-info"),
]
