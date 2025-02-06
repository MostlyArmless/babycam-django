from django.contrib import admin
from django.utils.html import format_html
from .models import MonitorDevice, AudioEvent


@admin.register(MonitorDevice)
class MonitorDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "stream_url",
        "is_active",
        "last_updated",
        "monitor_controls",
    )
    list_filter = ("is_active",)
    list_editable = ("stream_url",)

    def monitor_controls(self, obj):
        return format_html(
            '<button onclick="startMonitor({})">Start</button> '
            '<button onclick="stopMonitor({})">Stop</button>',
            obj.id,
            obj.id,
        )

    class Media:
        js = ("js/monitor_controls.js",)


@admin.register(AudioEvent)
class AudioEventAdmin(admin.ModelAdmin):
    list_display = ("device", "timestamp", "peak_value", "alert_level")
    list_filter = ("device", "alert_level", "timestamp")
    ordering = ("-timestamp",)
