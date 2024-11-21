# monitor/services/audio_monitor.py
import subprocess
import numpy as np
import logging
import threading
import time
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from ..models import MonitorDevice, AudioEvent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S.%f'  # Include milliseconds
)
logger = logging.getLogger(__name__)

class AudioMonitorService:
    _instances = {}
    
    @classmethod
    def get_monitor(cls, device_id):
        if device_id not in cls._instances:
            device = MonitorDevice.objects.get(id=device_id)
            cls._instances[device_id] = cls(device)
        return cls._instances[device_id]
    
    def __init__(self, device):
        self.device = device
        self.running = False
        self.thread = None
        self.channel_layer = get_channel_layer()
        
        # Audio processing & recording settings
        self.CHUNK = 4096
        self.RATE = 48000
        self.MIN_RECORDING_DURATION = 10  # seconds
        self.MAX_RECORDING_DURATION = 60  # seconds
        self.QUIET_PERIOD_THRESHOLD = 5   # seconds
        self.recording = False
        self.current_recording_path = None
        self.recording_start_time = None
        self.last_alert_time = None
        self.quiet_period_start = None
        
    def start_ffmpeg(self):
        """Start FFmpeg process for audio stream"""
        command = [
            'ffmpeg',
            '-loglevel', 'error',  # Only show errors
            '-i', self.device.stream_url,
            '-vn',  # Skip video
            '-acodec', 'pcm_s16le',
            '-ar', str(self.RATE),
            '-ac', '1',
            '-f', 'wav',
            'pipe:1'  # Output to stdout
        ]
        
        if self.device.username and self.device.password:
            import base64
            auth = base64.b64encode(
                f"{self.device.username}:{self.device.password}".encode()
            ).decode()
            command.insert(1, '-headers')
            command.insert(2, f'Authorization: Basic {auth}\r\n')
        
        logger.info(f"Starting FFmpeg with command: {' '.join(command)}")
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )

    def start_recording(self):
        """Start recording video and audio"""
        if self.recording:
            return
                
        self.recording = True
        self.recording_start_time = time.time()
        self.last_alert_time = time.time()
        self.quiet_period_start = None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_recording_path = f"recordings/{self.device.name}_{timestamp}.mp4"
        
        command = [
            'ffmpeg',
            '-y',  # Overwrite output files without asking
            '-i', self.device.stream_url,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-strict', 'experimental',
            '-f', 'mp4',
            self.current_recording_path
        ]
        
        if self.device.username and self.device.password:
            import base64
            auth = base64.b64encode(f"{self.device.username}:{self.device.password}".encode()).decode()
            command.insert(1, '-headers')
            command.insert(2, f'Authorization: Basic {auth}\r\n')

        self.recording_process = subprocess.Popen(command)
        logger.info(f"Started recording to {self.current_recording_path}")

    def stop_recording(self):
        """Stop current recording"""
        if not self.recording:
            return
            
        self.recording = False
        if hasattr(self, 'recording_process'):
            self.recording_process.terminate()
            self.recording_process.wait()
            logger.info("Stopped recording")
            self.current_recording_path = None

    def process_audio(self):
        """Main audio processing loop"""
        process = self.start_ffmpeg()
        process.stdout.read(44)  # Skip WAV header
        
        logger.info(f"Started monitoring for {self.device.name}")
        logger.info(f"Yellow threshold: {self.device.yellow_threshold}")
        logger.info(f"Red threshold: {self.device.red_threshold}")
        
        try:
            while self.running:
                audio_data = process.stdout.read(self.CHUNK)
                if not audio_data:
                    break
                
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                peak = int(np.max(np.abs(audio_array)))
                
                # Determine alert level
                alert_level = 'NONE'
                if peak >= self.device.red_threshold:
                    alert_level = 'RED'
                    if not self.recording:
                        self.start_recording()
                    logger.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} - RED ALERT - Loud noise detected! Peak: {peak}")
                elif peak >= self.device.yellow_threshold:
                    alert_level = 'YELLOW'
                    logger.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} - YELLOW ALERT - Moderate noise detected. Peak: {peak}")
                else:
                    logger.debug(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} - Current peak: {peak}")
                
                # Check if we should stop recording
                if self.recording and self.should_stop_recording(peak):
                    self.stop_recording()
                
                # Save significant events and broadcast
                if alert_level != 'NONE':
                    AudioEvent.objects.create(
                        device=self.device,
                        peak_value=peak,
                        alert_level=alert_level
                    )
                    self.broadcast_level(peak, alert_level)
                
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
        finally:
            process.terminate()
            process.wait()
            if self.recording:
                self.stop_recording()

    def broadcast_level(self, peak, alert_level):
        """Send audio level update via WebSocket"""
        message = {
            'type': 'audio_level',
            'device_id': self.device.id,
            'peak': peak,
            'alert_level': alert_level,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            async_to_sync(self.channel_layer.group_send)(
                f'monitor_{self.device.id}',
                {
                    'type': 'monitor_message',
                    'message': message
                }
            )
        except Exception as e:
            logger.error(f"Error broadcasting level: {e}")

    def start(self):
        """Start monitoring"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self.process_audio)
        self.thread.start()
        logger.info(f"Started monitoring thread for device: {self.device.name}")

    def stop(self):
        """Stop monitoring"""
        if not self.running:
            return
            
        logger.info(f"Stopping monitor for device: {self.device.name}")
        self.running = False
        
        # Force stop any FFmpeg processes
        if hasattr(self, 'recording_process'):
            try:
                self.recording_process.terminate()
                self.recording_process.wait(timeout=2)
            except:
                self.recording_process.kill()
        
        # Wait for the monitoring thread to finish
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=2)  # Reduced timeout
                if self.thread.is_alive():
                    logger.warning("Monitor thread didn't stop gracefully, forcing termination")
                    # We might want to force kill FFmpeg here too
                    import os
                    import signal
                    os.kill(os.getpid(), signal.SIGKILL)
            except:
                pass
        
        # Clear the instance from our registry
        if self.device.id in self._instances:
            del self._instances[self.device.id]
        
        logger.info(f"Monitor stopped for device: {self.device.name}")

    def should_stop_recording(self, current_peak):
        """Determine if recording should stop based on duration and sound level"""
        if not self.recording:
            return False
            
        current_time = time.time()
        recording_duration = current_time - self.recording_start_time
        
        # Always stop if we hit max duration
        if recording_duration >= self.MAX_RECORDING_DURATION:
            logger.info("Stopping recording: Max duration reached")
            return True
            
        # Don't stop if we haven't hit minimum duration
        if recording_duration < self.MIN_RECORDING_DURATION:
            return False
            
        # Handle quiet period tracking
        if current_peak < self.device.yellow_threshold:
            if self.quiet_period_start is None:
                self.quiet_period_start = current_time
            elif (current_time - self.quiet_period_start) >= self.QUIET_PERIOD_THRESHOLD:
                logger.info("Stopping recording: Quiet period threshold reached")
                return True
        else:
            self.quiet_period_start = None
            self.last_alert_time = current_time
            
        return False