from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class WebSocketInfoView(APIView):
    """GET /chat/ — documents the available realtime WebSocket endpoints."""

    permission_classes = [AllowAny]

    def get(self, request):
        scheme = "wss" if request.is_secure() else "ws"
        host = request.get_host()
        return Response(
            {
                "endpoints": {
                    "chat": f"{scheme}://{host}/ws/chat/<conversation_id>/?token=<access_jwt>",
                    "notifications": f"{scheme}://{host}/ws/notifications/?token=<access_jwt>",
                },
                "chat_protocol": {
                    "send": {"question": "string", "source_ids": ["uuid"], "top_k": 6},
                    "receive": ["citations", "token", "done", "error"],
                },
            }
        )
