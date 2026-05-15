from django.contrib import admin
from .models import LocationReading

@admin.register(LocationReading)
class LocationReadingAdmin(admin.ModelAdmin):
    list_display = ('device', 'latitude', 'longitude', 'speed', 'timestamp')
    list_filter = ('device',)
    readonly_fields = ('id', 'timestamp')
