"""
alerts/tasks.py

NOTE: Celery has been removed from this project.
SMS is now handled directly by the ESP32 hardware via SIM800L GSM module.
The ESP32 sends SMS offline using the physical SIM card — no internet needed.

This module now contains a plain Python function (not a Celery task) that:
  1. Logs the alert to the console (for local development visibility)
  2. Pushes a real-time WebSocket notification to the parent dashboard

Called directly (not via .delay()) from alerts/views.py
"""

from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import AlertEvent
from .serializers import AlertEventSerializer


def send_alert_notification(alert_id: str):
    """
    Called synchronously from AlertEventViewSet.create() when ESP32 triggers an alert.

    What this does:
      1. Logs alert details to the console (dev visibility)
      2. Pushes real-time WebSocket message to the parent dashboard

    What the ESP32 does independently (no backend needed):
      - Sends SMS directly via SIM800L using the physical SIM card
      - Works completely offline — no WiFi or internet required
    """
    alert = (
        AlertEvent.objects
        .select_related('device__owner')
        .get(id=alert_id)
    )

    parent_phone = alert.device.owner.phone
    msg = (
        f'SAFETY ALERT ({alert.alert_type}): '
        f'Lat {alert.latitude}, Lon {alert.longitude}. '
        f'Time: {alert.timestamp:%H:%M}'
    )

    # ── Console log (development visibility) ──────────────────────────────────
    print('\n' + '=' * 60)
    print(f'🚨  ALERT RECEIVED — {alert.alert_type}')
    print(f'   Device  : {alert.device.name}')
    print(f'   Parent  : {parent_phone}')
    print(f'   Message : {msg}')
    print(f'   SMS     : Sent directly by ESP32 SIM800L (offline capable)')
    print('=' * 60 + '\n')

    # ── Push real-time WebSocket notification to parent dashboard ──────────────
    # This notifies any open browser/app dashboard instantly. The full serialized
    # alert is sent so the dashboard has id, timestamp, device_name,
    # alert_type_display, sms_sent and resolved without a follow-up REST call.
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'device_{alert.device_id}',
        {
            'type':  'alert_event',
            'alert': AlertEventSerializer(alert).data,
        },
    )
