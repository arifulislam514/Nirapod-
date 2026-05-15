from django.contrib import admin
from .models import Device

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'last_seen', 'battery_pct')
    list_filter = ('is_active',)
    search_fields = ('name', 'owner__email', 'device_token')
    readonly_fields = ('id', 'device_token', 'last_seen')
