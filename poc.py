import cv2
import numpy as np
import requests
import threading
import time
from datetime import datetime
import os
from urllib.parse import urljoin
import pyaudio
import wave
import queue
import logging

class IPWebcamMonitor:
    def __init__(self, base_url, username, password, yellow_threshold=50, red_threshold=75):
        """
        Initialize the monitor with IP Webcam details and thresholds.
        
        Args:
            base_url: Base URL of IP Webcam (e.g., 'http://192.168.0.222:8080')
            username: Authentication username
            password: Authentication password
            yellow_threshold: Audio level for yellow alert (0-100)
            red_threshold: Audio level for red alert (0-100)
        """
        self.base_url = base_url
        self.auth = (username, password)
        self.yellow_threshold = yellow_threshold
        self.red_threshold = red_threshold
        self.recording = False
        self.running = False
        self.audio_queue = queue.Queue()
        
        # Create recordings directory if it doesn't exist
        self.recordings_dir = "recordings"
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_audio_level(self):
        """Get current audio level from IP Webcam."""
        try:
            response = requests.get(urljoin(self.base_url, "audio_level"),
                                 auth=self.auth,
                                 timeout=1)
            if response.status_code == 200:
                return float(response.text)
            return 0
        except Exception as e:
            self.logger.error(f"Error getting audio level: {e}")
            return 0

    def start_recording(self):
        """Start recording video and audio."""
        if self.recording:
            return
            
        self.recording = True
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = os.path.join(self.recordings_dir, f"recording_{timestamp}.mp4")
        
        # Start video recording using ffmpeg
        stream_url = urljoin(self.base_url, "video")
        cmd = [
            'ffmpeg',
            '-i', stream_url,
            '-c:v', 'copy',
            '-c:a', 'aac',
            video_filename
        ]
        
        self.ffmpeg_process = subprocess.Popen(cmd)
        self.logger.info(f"Started recording to {video_filename}")

    def stop_recording(self):
        """Stop current recording."""
        if not self.recording:
            return
            
        self.recording = False
        if hasattr(self, 'ffmpeg_process'):
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
            self.logger.info("Stopped recording")

    def monitor_audio_levels(self):
        """Monitor audio levels and trigger recording."""
        last_high_level_time = 0
        recording_cooldown = 60  # 1 minute cooldown

        while self.running:
            level = self.get_audio_level()
            current_time = time.time()
            
            if level >= self.red_threshold:
                self.logger.info(f"Red alert! Audio level: {level}")
                if not self.recording:
                    self.start_recording()
                last_high_level_time = current_time
            elif level >= self.yellow_threshold:
                self.logger.info(f"Yellow alert! Audio level: {level}")
                if not self.recording:
                    self.start_recording()
                last_high_level_time = current_time
            elif self.recording and (current_time - last_high_level_time) > recording_cooldown:
                self.stop_recording()
            
            time.sleep(0.1)  # Check levels 10 times per second

    def start(self):
        """Start the monitoring system."""
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_audio_levels)
        self.monitor_thread.start()
        self.logger.info("Monitoring started")

    def stop(self):
        """Stop the monitoring system."""
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join()
        self.stop_recording()
        self.logger.info("Monitoring stopped")

def main():
    # Example usage
    monitor = IPWebcamMonitor(
        base_url="http://192.168.0.222:8080",
        username="mike",
        password="asdfghjkl",
        yellow_threshold=50,  # Adjust these thresholds based on testing
        red_threshold=75
    )
    
    try:
        monitor.start()
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        print("\nMonitoring stopped")

if __name__ == "__main__":
    main()