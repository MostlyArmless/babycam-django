from django.core.management.base import BaseCommand
from monitor.models import MonitorDevice
from monitor.services.audio_monitor import AudioMonitorService
import time

class Command(BaseCommand):
    help = 'Test audio monitoring for a specific device'

    def handle(self, *args, **options):
        try:
            # Get the first active device
            device = MonitorDevice.objects.filter(is_active=True).first()
            if not device:
                self.stdout.write(self.style.ERROR('No active devices found'))
                return

            self.stdout.write(self.style.SUCCESS(f'Starting monitor for {device.name}'))
            
            # Start monitoring
            monitor = AudioMonitorService.get_monitor(device.id)
            monitor.start()
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('Stopping monitor...'))
                monitor.stop()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))