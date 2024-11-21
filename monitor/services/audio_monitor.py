import base64
import glob
import os
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
        self.buffer_process = None
        self.last_alert_time = 0
        self.RECORDING_COOLDOWN = 10  # seconds to keep recording after noise drops

    def start_buffer_process(self):
        """Start FFmpeg process for buffer recording"""
        buffer_dir = "buffer"
        os.makedirs(buffer_dir, exist_ok=True)
        
        command = [
            'ffmpeg',
            '-i', self.device.stream_url,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-f', 'segment',
            '-segment_time', '2',
            '-segment_wrap', '5',
            '-segment_list_size', '5',
            '-segment_format', 'mp4',
            f'{buffer_dir}/buffer_%d.mp4'
        ]
        
        if self.device.username and self.device.password:
            auth = base64.b64encode(f"{self.device.username}:{self.device.password}".encode()).decode()
            command.insert(1, '-headers')
            command.insert(2, f'Authorization: Basic {auth}\r\n')
        
        return subprocess.Popen(command)
        
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
        """Start recording with pre-roll buffer"""
        if self.recording:
            return
                
        self.recording = True
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_recording_path = f"recordings/{self.device.name}_{timestamp}.mp4"
        
        # Concatenate buffer files with current stream
        buffer_files = sorted(glob.glob("buffer/buffer_*.mp4"))
        
        # Create file list for FFmpeg
        with open("buffer/filelist.txt", "w") as f:
            for bf in buffer_files:
                f.write(f"file '{os.path.abspath(bf)}'\n")
        
        # Start recording process that concatenates buffer with live stream
        command = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', 'buffer/filelist.txt',  # Buffer files
            '-i', self.device.stream_url,  # Live stream
            '-c', 'copy',                  # Copy without re-encoding
            self.current_recording_path
        ]
        
        if self.device.username and self.device.password:
            import base64
            auth = base64.b64encode(f"{self.device.username}:{self.device.password}".encode()).decode()
            command.insert(1, '-headers')
            command.insert(2, f'Authorization: Basic {auth}\r\n')

        self.recording_process = subprocess.Popen(command)
        logger.info(f"Started recording to {self.current_recording_path} (includes pre-roll buffer)")

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
        
        try:
            while self.running:
                audio_data = process.stdout.read(self.CHUNK)
                if not audio_data:
                    break
                
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                peak = int(np.max(np.abs(audio_array)))
                current_time = time.time()
                
                if peak >= self.device.red_threshold:
                    alert_level = 'RED'
                    self.last_alert_time = current_time
                    logger.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} - RED ALERT - Loud noise detected! Peak: {peak}")
                    if not self.recording:
                        logger.info("Starting recording with buffer due to RED alert")
                        self.start_recording_with_buffer()
                elif peak >= self.device.yellow_threshold:
                    alert_level = 'YELLOW'
                    self.last_alert_time = current_time
                    logger.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} - YELLOW ALERT - Moderate noise detected. Peak: {peak}")
                else:
                    alert_level = 'NONE'
                    # Only stop recording if we've been quiet for RECORDING_COOLDOWN seconds
                    if self.recording and (current_time - self.last_alert_time) > self.RECORDING_COOLDOWN:
                        logger.info(f"Noise level normal for {self.RECORDING_COOLDOWN} seconds, stopping recording")
                        self.stop_recording()
                
                if alert_level != 'NONE':
                    AudioEvent.objects.create(
                        device=self.device,
                        peak_value=peak,
                        alert_level=alert_level
                    )
                
                time.sleep(0.1)
                
        finally:
            if self.buffer_process:
                self.buffer_process.terminate()
                self.buffer_process.wait(timeout=2)

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
        # Start buffer process
        self.buffer_process = self.start_ffmpeg_buffer()

        # Start monitoring thread
        self.thread = threading.Thread(target=self.process_audio)
        self.thread.start()
        logger.info(f"Started monitoring thread for device: {self.device.name}")

    def stop(self):
        """Stop monitoring"""
        if not self.running:
            return
            
        logger.info(f"Stopping monitor for device: {self.device.name}")
        self.running = False

        if self.buffer_process:
            self.buffer_process.terminate()
            self.buffer_process.wait(timeout=2)
        
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

    def start_ffmpeg_buffer(self):
        """Start FFmpeg process that maintains a rolling buffer of segments"""
        buffer_dir = "buffer"
        os.makedirs(buffer_dir, exist_ok=True)
        
        command = [
            'ffmpeg',
            '-i', self.device.stream_url,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-f', 'segment',
            '-segment_time', '2',          # Create 2-second segments
            '-segment_wrap', '5',          # Keep only last 5 segments (10 seconds)
            '-segment_list_size', '5',
            '-segment_format', 'mp4',
            f'{buffer_dir}/buffer_%d.mp4'  # Buffer files
        ]
        
        if self.device.username and self.device.password:
            import base64
            auth = base64.b64encode(f"{self.device.username}:{self.device.password}".encode()).decode()
            command.insert(1, '-headers')
            command.insert(2, f'Authorization: Basic {auth}\r\n')
        
        return subprocess.Popen(command)
    
    def start_recording_with_buffer(self):
        """Start recording including buffer content"""
        if self.recording:
            logger.info("Recording already in progress, skipping")
            return
                
        self.recording = True
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_recording_path = f"recordings/{self.device.name}_{timestamp}.mp4"

        os.makedirs('recordings', exist_ok=True)

        # Wait briefly for any ongoing buffer writes to complete
        time.sleep(0.5)

        # Get list of buffer files
        buffer_files = sorted(glob.glob("buffer/buffer_*.mp4"))
        logger.info(f"Found {len(buffer_files)} buffer files to include in recording")

        if not buffer_files:
            logger.warning("No buffer files found, starting direct recording")
            self.start_direct_recording()
            return
            
        # Create concat file
        with open("buffer/filelist.txt", "w") as f:
            for bf in buffer_files:
                if os.path.getsize(bf) > 0:  # Only include non-empty files
                    f.write(f"file '{os.path.abspath(bf)}'\n")

    def start_direct_recording(self):
        """Start recording without buffer when buffer isn't available"""
        command = [
            'ffmpeg',
            '-y',
            '-i', self.device.stream_url,
        ]
        
        if self.device.username and self.device.password:
            auth = base64.b64encode(f"{self.device.username}:{self.device.password}".encode()).decode()
            command.extend(['-headers', f'Authorization: Basic {auth}\r\n'])
        
        command.extend([
            '-c', 'copy',
            self.current_recording_path
        ])

        logger.info(f"Starting direct recording with command: {' '.join(command)}")
        self.recording_process = subprocess.Popen(command)