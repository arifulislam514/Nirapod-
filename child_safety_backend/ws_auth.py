"""
WebSocket JWT authentication middleware for Django Channels.

Browsers cannot set custom headers on a WebSocket handshake, so the access
token is passed in the query string:

    wss://host/ws/device/<device_id>/?token=<access_token>

This middleware validates that token with SimpleJWT and puts the matching
user on ``scope['user']``. Invalid/absent tokens result in an AnonymousUser,
which the consumer rejects.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def _get_user(token_str):
    """Resolve a user from a raw access-token string, or AnonymousUser."""
    try:
        token = AccessToken(token_str)
        user_id = token.get('user_id')
        if user_id is None:
            return AnonymousUser()
        return User.objects.get(id=user_id)
    except (TokenError, User.DoesNotExist, KeyError, ValueError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Populate scope['user'] from a ?token=<access> query-string param."""

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get('query_string', b'').decode())
        token_list = query.get('token')
        if token_list:
            scope['user'] = await _get_user(token_list[0])
        else:
            scope['user'] = AnonymousUser()
        return await super().__call__(scope, receive, send)
