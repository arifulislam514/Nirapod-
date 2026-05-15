import uuid
from django.db import models
from accounts.models import CustomUser


class Device(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='devices',
    )
    name = models.CharField(max_length=100)  # e.g. "Riya School Device"
    device_token = models.CharField(
        max_length=64,
        unique=True,
        help_text='Static token sent by ESP32 in X-Device-Token header',
    )
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)  # updated on every POST
    battery_pct = models.IntegerField(default=100)  # 0–100

    class Meta:
        ordering = ['-last_seen']

    def __str__(self):
        return f'{self.name} ({self.owner.email})'
