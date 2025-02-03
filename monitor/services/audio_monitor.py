import queue
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

WAV_HEADER_LENGTH = 44

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S.%f'  # Include milliseconds
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure DEBUG level is enabled

class AudioMonitorService:
    _instances = {}
    
    @classmethod
    def get_monitor(cls, device_id):
        if device_id not in cls._instances:
            device = MonitorDevice.objects.get(id=device_id)
            cls._instances[device_id] = cls(device)
        return cls._instances[device_id]
    
    def __init__(self, device: MonitorDevice):
        self.device = device
        self.running = False
        self.thread = None
        self.channel_layer = get_channel_layer()
        
        # Audio processing & recording settings
        self.CHUNK = 4096
        self.RATE = 48000
        self.MIN_RECORDING_DURATION = 1  # seconds
        self.MAX_RECORDING_DURATION = 5  # seconds
        self.QUIET_PERIOD_THRESHOLD = 3   # seconds
        self.recording = False
        self.current_recording_path = None
        self.recording_start_time = None
        self.last_alert_time = None
        self.quiet_period_start = None
        self.recording_lock = threading.Lock()
        self.event_queue = queue.Queue()
        self.recording_process = None
        
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
            '-y'  # Overwrite output files without asking
        ]
        
        if self.device.is_authenticated:
            if not self.device.username or not self.device.password:
                logger.error(f"Device {self.device.name} is marked as authenticated but missing credentials")
                self.recording = False
                return
            import base64
            auth = base64.b64encode(f"{self.device.username}:{self.device.password}".encode()).decode()
            command.extend(['-headers', f'Authorization: Basic {auth}\r\n'])
        
        command.extend([
            '-i', self.device.stream_url,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-strict', 'experimental',
            '-f', 'mp4',
            self.current_recording_path
        ])

        try:
            self.recording_process = subprocess.Popen(command)
            logger.info(f"Started recording to {self.current_recording_path}")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.recording = False

    def stop_recording(self):
        """Stop current recording"""
        if not self.recording:
            return
            
        try:
            if self.recording_process:
                self.recording_process.terminate()
                self.recording_process.wait(timeout=2)
                logger.info("Stopped recording")
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            if self.recording_process:
                self.recording_process.kill()
        finally:
            self.recording = False
            self.recording_process = None
            self.current_recording_path = None

    def process_audio(self):
        ffmpeg_process = self.start_ffmpeg()
        if ffmpeg_process.stdout is None:
            raise RuntimeError("Failed to capture ffmpeg stdout.")
        ffmpeg_process.stdout.read(WAV_HEADER_LENGTH)  # Skip WAV header
        
        logger.info(f"Started monitoring for {self.device.name}")
        logger.info(f"Yellow threshold: {self.device.yellow_threshold}")
        logger.info(f"Red threshold: {self.device.red_threshold}")
        
        try:
            while self.running:
                audio_data = ffmpeg_process.stdout.read(self.CHUNK)
                if not audio_data:
                    break
                
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                peak = int(np.max(np.abs(audio_array)))
                
                # Determine alert level
                alert_level = 'NONE'
                if peak >= self.device.red_threshold:
                    alert_level = 'RED'
                    logger.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} - RED ALERT - Loud noise detected! Peak: {peak}")
                    if not self.recording:
                        self.start_recording()
                    self.last_alert_time = time.time()
                    self.quiet_period_start = None
                elif peak >= self.device.yellow_threshold:
                    alert_level = 'YELLOW'
                    logger.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} - YELLOW ALERT - Moderate noise detected. Peak: {peak}")
                    self.last_alert_time = time.time()
                    self.quiet_period_start = None
                
                # Check recording status
                if self.recording:
                    current_time = time.time()
                    if self.recording_start_time is None:
                        recording_duration = 0
                    else:
                        recording_duration = current_time - self.recording_start_time
                    
                    # Start quiet period tracking if below yellow threshold
                    if peak < self.device.yellow_threshold:
                        if self.quiet_period_start is None:
                            self.quiet_period_start = current_time
                    else:
                        self.quiet_period_start = None
                    
                    # Check if we should stop recording
                    should_stop = False
                    if recording_duration >= self.MAX_RECORDING_DURATION:
                        logger.info("Max recording duration reached")
                        should_stop = True
                    elif recording_duration >= self.MIN_RECORDING_DURATION:
                        if self.quiet_period_start and (current_time - self.quiet_period_start) >= self.QUIET_PERIOD_THRESHOLD:
                            logger.info("Quiet period threshold reached")
                            should_stop = True
                    
                    if should_stop:
                        self.stop_recording()
                
                # Save events
                if alert_level != 'NONE':
                    AudioEvent.objects.create(
                        device=self.device,
                        peak_value=peak,
                        alert_level=alert_level
                    )
                    self.broadcast_level(peak, alert_level)
                
                time.sleep(0.01)  # Reduced sleep time
                
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
        finally:
            if self.recording:
                self.stop_recording()
            ffmpeg_process.terminate()
            ffmpeg_process.wait()

    def broadcast_level(self, peak, alert_level):
        """Send audio level update via WebSocket"""
        try:
            channel_layer = get_channel_layer()
            if channel_layer is None:
                logger.error("No channel layer available!")
                return

            message = {
                'type': 'audio_level',
                'device_id': self.device.id,
                'peak': peak,
                'alert_level': alert_level,
                'timestamp': datetime.now().isoformat()
            }
            
            group_name = f'monitor_{self.device.id}'
            logger.debug(f"Broadcasting to group {group_name}: {message}")
            
            # Get list of channels in group (for debugging)
            channels = getattr(channel_layer, '_groups', {}).get(group_name, set())
            logger.debug(f"Current channels in group {group_name}: {channels}")

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'monitor_message',
                    'message': message
                }
            )
            logger.debug(f"Broadcast complete: {peak} ({alert_level})")
        except Exception as e:
            logger.error(f"Error broadcasting level: {e}", exc_info=True)

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
        
        try:
            # Stop recording if it's running
            if self.recording and self.recording_process:
                try:
                    self.recording_process.terminate()
                    self.recording_process.wait(timeout=2)
                    logger.info("Stopped recording")
                except:
                    # If terminate fails, try to force kill
                    if self.recording_process:  # Check again in case it changed
                        self.recording_process.kill()
                finally:
                    self.recording = False
                    self.recording_process = None
                    self.current_recording_path = None
            
            # Clear the instance from our registry
            if self.device.id in self._instances:
                del self._instances[self.device.id]
                
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info(f"Monitor stopped for device: {self.device.name}")

    def should_stop_recording(self, current_peak):
        """Determine if recording should stop based on duration and sound level"""
        if not self.recording:
            return False
            
        current_time = time.time()
        recording_duration = 0 if self.recording_start_time is None else current_time - self.recording_start_time
        
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
    
    def process_queued_events(self):
        """Process any queued events without blocking"""
        try:
            while True:
                event = self.event_queue.get_nowait()
                # Save to database
                AudioEvent.objects.create(
                    device=self.device,
                    peak_value=event['peak'],
                    alert_level=event['alert_level']
                )
                # Broadcast via WebSocket
                self.broadcast_level(event['peak'], event['alert_level'])
                self.event_queue.task_done()
        except queue.Empty:
            pass  # No more events to process