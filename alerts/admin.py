from django.contrib import admin
from .models import AlertEvent


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ('alert_type', 'device', 'sms_sent', 'resolved', 'timestamp')
    list_filter = ('alert_type', 'resolved', 'sms_sent')
    search_fields = ('device__name', 'device__owner__email')
    ordering = ('-timestamp',)
    readonly_fields = ('id', 'sms_sent', 'sms_sent_at', 'timestamp')
