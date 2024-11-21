# monitor/management/commands/test_monitor.py
from django.core.management.base import BaseCommand
from monitor.models import MonitorDevice
from monitor.services.audio_monitor import AudioMonitorService
import time
import signal

class Command(BaseCommand):
    help = 'Test audio monitoring for a specific device'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = None
        self.keep_running = True

    def handle(self, *args, **options):
        def signal_handler(signum, frame):
            self.stdout.write(self.style.WARNING('Stopping monitor...'))
            self.keep_running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # Get the first active device
            device = MonitorDevice.objects.filter(is_active=True).first()
            if not device:
                self.stdout.write(self.style.ERROR('No active devices found'))
                return

            self.stdout.write(self.style.SUCCESS(f'Starting monitor for {device.name}'))
            
            # Start monitoring
            self.monitor = AudioMonitorService.get_monitor(device.id)
            self.monitor.start()
            
            # Keep the script running
            while self.keep_running:
                time.sleep(1)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
        finally:
            if self.monitor:
                self.monitor.stop()