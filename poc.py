import subprocess
import numpy as np
import logging
import threading
import time
import pyaudio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudioMonitor:
    def __init__(self, stream_url, username=None, password=None):
        self.stream_url = stream_url
        self.username = username
        self.password = password
        self.running = False
        
        # Audio settings
        self.CHUNK = 4096
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 48000
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True
        )

    def start_ffmpeg(self):
        command = [
            'ffmpeg',
            '-i', self.stream_url,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', str(self.RATE),
            '-ac', '1',
            '-f', 'wav',
            '-'
        ]
        
        if self.username and self.password:
            import base64
            auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            command.insert(1, '-headers')
            command.insert(2, f'Authorization: Basic {auth}\r\n')
        
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )

    def process_audio(self):
        process = self.start_ffmpeg()
        
        # Skip WAV header
        process.stdout.read(44)
        
        logger.info("Starting audio processing loop")
        
        try:
            while self.running:
                audio_data = process.stdout.read(self.CHUNK)
                if not audio_data:
                    break
                
                # Convert to numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Calculate various metrics
                rms = np.sqrt(np.mean(np.square(audio_array)))
                peak = np.max(np.abs(audio_array))
                mean = np.mean(np.abs(audio_array))
                
                logger.info(f"Raw metrics - RMS: {rms:.1f}, Peak: {peak}, Mean: {mean:.1f}")
                
                # Play audio
                self.stream.write(audio_data)
                
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
        finally:
            process.terminate()
            process.wait()

    def start(self):
        self.running = True
        self.audio_thread = threading.Thread(target=self.process_audio)
        self.audio_thread.start()
        logger.info("Audio monitoring started")

    def stop(self):
        self.running = False
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join()
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        logger.info("Audio monitoring stopped")

def main():
    monitor = AudioMonitor(
        stream_url="http://192.168.0.222:8080/video/live.m3u8",
        username="mike",
        password="asdfghjkl"
    )
    
    try:
        monitor.start()
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()

if __name__ == "__main__":
    main()