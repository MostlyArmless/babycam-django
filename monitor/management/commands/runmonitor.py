from django.core.management.base import BaseCommand
from monitor.models import MonitorDevice
from monitor.services.audio_monitor import AudioMonitorService

class Command(BaseCommand):
    help = 'Start audio monitoring for all active devices'

    def handle(self, *args, **options):
        devices = MonitorDevice.objects.filter(is_active=True)
        
        for device in devices:
            try:
                monitor = AudioMonitorService.get_monitor(device.id)
                monitor.start()
                self.stdout.write(
                    self.style.SUCCESS(f'Started monitoring {device.name}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to start {device.name}: {e}')
                )