from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from devices.models import Device
from .models import LocationReading


def record_location(device: Device, data: dict) -> LocationReading:
    """
    Persist a GPS reading and push a real-time update to the parent dashboard.
    Also updates Device.last_seen and battery_pct.
    """
    reading = LocationReading.objects.create(
        device=device,
        latitude=data['latitude'],
        longitude=data['longitude'],
        accuracy=data.get('accuracy'),
        speed=data.get('speed'),
    )

    # Update device heartbeat
    device.last_seen = timezone.now()
    update_fields = ['last_seen']
    if 'battery_pct' in data:
        device.battery_pct = data['battery_pct']
        update_fields.append('battery_pct')
    device.save(update_fields=update_fields)

    # Push live update via WebSocket to parent dashboard
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'device_{device.id}',
        {
            'type': 'location_update',
            'lat': str(reading.latitude),
            'lon': str(reading.longitude),
            'timestamp': reading.timestamp.isoformat(),
            'speed': str(reading.speed) if reading.speed is not None else None,
            'accuracy': str(reading.accuracy) if reading.accuracy is not None else None,
        },
    )

    return reading
