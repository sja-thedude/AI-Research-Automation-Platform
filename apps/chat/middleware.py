"""JWT authentication middleware for Channels WebSocket connections.

Browsers can't set Authorization headers on WebSocket handshakes, so the token
is passed as a query param: ws://host/ws/chat/?token=<access_jwt>. This
middleware validates it and attaches the user to the connection scope.
"""
from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user(validated_token):
    from rest_framework_simplejwt.authentication import JWTAuthentication

    try:
        return JWTAuthentication().get_user(validated_token)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        from rest_framework_simplejwt.tokens import AccessToken

        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]

        scope["user"] = AnonymousUser()
        if token:
            try:
                scope["user"] = await _get_user(AccessToken(token))
            except (InvalidToken, TokenError):
                pass

        return await super().__call__(scope, receive, send)
