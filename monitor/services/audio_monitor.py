# monitor/services/audio_monitor.py
import subprocess
import numpy as np
import logging
import threading
import asyncio
import json
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from ..models import MonitorDevice, AudioEvent

logger = logging.getLogger(__name__)

class AudioMonitorService:
    _instances = {}  # Class variable to track monitor instances
    
    # Use the singleton pattern to ensure we're only using one monitor per device
    @classmethod
    def get_monitor(cls, device_id):
        """Get or create monitor instance for a device"""
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
            '-i', self.device.stream_url,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', str(self.RATE),
            '-ac', '1',
            '-f', 'wav',
            '-'
        ]
        
        if self.device.username and self.device.password:
            import base64
            auth = base64.b64encode(
                f"{self.device.username}:{self.device.password}".encode()
            ).decode()
            command.insert(1, '-headers')
            command.insert(2, f'Authorization: Basic {auth}\r\n')
        
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )

    def start_recording(self):
        """Start recording audio/video"""
        if self.recording:
            return
            
        self.recording = True
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_recording_path = f"recordings/{self.device.name}_{timestamp}.mp4"
        
        # Start recording process
        command = [
            'ffmpeg',
            '-i', self.device.stream_url,
            '-c:v', 'copy',
            '-c:a', 'aac',
            self.current_recording_path
        ]
        
        if self.device.username and self.device.password:
            import base64
            auth = base64.b64encode(
                f"{self.device.username}:{self.device.password}".encode()
            ).decode()
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
            
            # Save recording info to database
            AudioEvent.objects.create(
                device=self.device,
                recording_path=self.current_recording_path
            )
            self.current_recording_path = None

    def process_audio(self):
        """Main audio processing loop"""
        process = self.start_ffmpeg()
        
        # Skip WAV header
        process.stdout.read(44)
        
        try:
            while self.running:
                # Read and process audio chunk
                audio_data = process.stdout.read(self.CHUNK)
                if not audio_data:
                    break
                
                # Calculate peak value
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                peak = np.max(np.abs(audio_array))
                
                # Determine alert level
                alert_level = 'NONE'
                if peak >= self.device.red_threshold:
                    alert_level = 'RED'
                    if not self.recording:
                        self.start_recording()
                elif peak >= self.device.yellow_threshold:
                    alert_level = 'YELLOW'
                    if not self.recording:
                        self.start_recording()
                elif self.recording:
                    # Stop recording if level has dropped
                    self.stop_recording()
                
                # Send update via WebSocket
                self.broadcast_level(peak, alert_level)
                
                # Save significant events to database
                if alert_level != 'NONE':
                    AudioEvent.objects.create(
                        device=self.device,
                        peak_value=int(peak),
                        alert_level=alert_level
                    )
                
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
        finally:
            process.terminate()
            process.wait()
            self.stop_recording()

    def broadcast_level(self, peak, alert_level):
        """Send audio level update via WebSocket"""
        message = {
            'type': 'audio_level',
            'device_id': self.device.id,
            'peak': int(peak),
            'alert_level': alert_level,
            'timestamp': datetime.now().isoformat()
        }
        
        async_to_sync(self.channel_layer.group_send)(
            f'monitor_{self.device.id}',
            {
                'type': 'monitor_message',
                'message': message
            }
        )

    def start(self):
        """Start monitoring"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self.process_audio)
        self.thread.start()
        logger.info(f"Started monitoring for device: {self.device.name}")

    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.stop_recording()
        logger.info(f"Stopped monitoring for device: {self.device.name}")