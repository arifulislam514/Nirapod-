from celery import shared_task
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import AlertEvent


@shared_task
def send_sms_alert(alert_id: str):
    """
    DEV MODE — prints the SMS to the Celery terminal instead of sending a real SMS.
    To switch to a real provider later (Twilio / BulkSMSBD), replace the
    console block below with an HTTP call to your SMS API.

    Also pushes the alert to the parent's WebSocket dashboard channel.
    Called by AlertEventViewSet.perform_create() via .delay()
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

    # ── DEV: Console SMS (no real API needed) ─────────────────────────────────
    print('\n' + '=' * 60)
    print('📱  SIMULATED SMS (dev mode)')
    print(f'   To      : {parent_phone}')
    print(f'   Message : {msg}')
    print('=' * 60 + '\n')

    alert.sms_sent = True
    alert.sms_sent_at = timezone.now()
    alert.save(update_fields=['sms_sent', 'sms_sent_at'])
    # ── END DEV block ──────────────────────────────────────────────────────────

    # ── Push via WebSocket to parent dashboard ─────────────────────────────────
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'device_{alert.device_id}',
        {
            'type': 'alert_event',
            'alert_type': alert.alert_type,
            'lat': str(alert.latitude) if alert.latitude else None,
            'lon': str(alert.longitude) if alert.longitude else None,
        },
    )
