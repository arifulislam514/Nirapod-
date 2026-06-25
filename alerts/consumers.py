import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from devices.models import Device


class DeviceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket endpoint: ws://host/ws/device/{device_id}/?token=<access_token>

    The parent's React dashboard connects here to receive:
      - Real-time GPS location updates (pushed by locations/services.py)
      - Alert notifications          (pushed by alerts/tasks.py)

    Access control:
      - The JWT access token must be supplied as a ?token= query param
        (browsers can't set WS headers); JWTAuthMiddleware resolves scope['user'].
      - The connecting user must OWN the device, otherwise the socket is closed.

    Each device gets its own channel group: device_{device_id}
    """

    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        self.group_name = f'device_{self.device_id}'

        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close(code=4001)          # unauthenticated
            return
        if not await self._user_owns_device(user, self.device_id):
            await self.close(code=4003)          # authenticated but not the owner
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        # group_name is only set once connect() got far enough to assign it
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def _user_owns_device(self, user, device_id):
        return Device.objects.filter(id=device_id, owner=user).exists()

    # ── Handlers called by channel layer group_send ────────────────────────────

    async def location_update(self, event):
        """Forwards a real-time GPS reading to the connected browser."""
        await self.send(text_data=json.dumps({
            'type': 'location',
            'lat': event['lat'],
            'lon': event['lon'],
            'ts': event['timestamp'],
            'speed': event.get('speed'),
            'accuracy': event.get('accuracy'),
        }))

    async def alert_event(self, event):
        """Forwards a new alert notification (full serialized object) to the browser."""
        payload = {'type': 'alert'}
        payload.update(event.get('alert', {}))
        await self.send(text_data=json.dumps(payload, default=str))
