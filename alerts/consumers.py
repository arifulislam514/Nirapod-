import json
from channels.generic.websocket import AsyncWebsocketConsumer


class DeviceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket endpoint: ws://host/ws/device/{device_id}/

    The parent's React dashboard connects here to receive:
      - Real-time GPS location updates (pushed by locations/services.py)
      - Alert notifications          (pushed by alerts/tasks.py)

    Each device gets its own channel group: device_{device_id}
    """

    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        self.group_name = f'device_{self.device_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ── Handlers called by channel layer group_send ────────────────────────────

    async def location_update(self, event):
        """Forwards a real-time GPS reading to the connected browser."""
        await self.send(text_data=json.dumps({
            'type': 'location',
            'lat': event['lat'],
            'lon': event['lon'],
            'ts': event['timestamp'],
        }))

    async def alert_event(self, event):
        """Forwards a new alert notification to the connected browser."""
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'alert_type': event['alert_type'],
            'lat': event.get('lat'),
            'lon': event.get('lon'),
        }))
