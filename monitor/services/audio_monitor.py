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
        
        # Audio processing settings
        self.CHUNK = 4096
        self.RATE = 48000
        self.recording = False
        self.current_recording_path = None
        
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_recording_path = f"recordings/{self.device.name}_{timestamp}.mp4"
        
        command = [
            'ffmpeg',
            '-i', self.device.stream_url,
            '-c:v', 'copy',        # Copy video stream without re-encoding
            '-c:a', 'aac',         # Use AAC for audio
            '-strict', 'experimental',  # Allow experimental codecs
            '-f', 'mp4',           # Force MP4 format
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
        
        # Skip WAV header
        process.stdout.read(44)
        
        logger.info(f"Started monitoring for {self.device.name}")
        logger.info(f"Yellow threshold: {self.device.yellow_threshold}")
        logger.info(f"Red threshold: {self.device.red_threshold}")
        
        try:
            while self.running:
                # Read and process audio chunk
                audio_data = process.stdout.read(self.CHUNK)
                if not audio_data:
                    break
                
                # Calculate peak value
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
                    if not self.recording:
                        self.start_recording()
                elif self.recording:
                    # Stop recording if level has dropped
                    self.stop_recording()
                
                    # Send update via WebSocket
                    self.broadcast_level(peak, alert_level)

                    logger.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} - YELLOW ALERT - Moderate noise detected. Peak: {peak}")
                else:
                    logger.debug(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} - Current peak: {peak}")
                
                # Save significant events to database
                if alert_level != 'NONE':
                    AudioEvent.objects.create(
                        device=self.device,
                        peak_value=peak,
                        alert_level=alert_level
                    )
                
                # Broadcast level via WebSocket
                self.broadcast_level(peak, alert_level)
                
                time.sleep(0.1)  # Small delay to prevent overwhelming the system
                
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
        finally:
            process.terminate()
            process.wait()

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