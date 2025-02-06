from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "monitor"

    def ready(self):
        from .services.audio_monitor import AudioMonitorService
        from .models import MonitorDevice

        # Start audio monitoring for all active devices
        for device in MonitorDevice.objects.filter(is_active=True):
            monitor = AudioMonitorService.get_monitor(device.id)
            monitor.start()
