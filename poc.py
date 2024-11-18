import subprocess
import numpy as np
import sys
import logging
import threading
import time
import wave
import pyaudio

logging.basicConfig(
    level=logging.DEBUG,
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
        self.RATE = 48000  # From FFmpeg debug output
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True
        )

    def start_ffmpeg(self):
        """Start FFmpeg process to get audio from stream"""
        command = [
            'ffmpeg',
            '-i', self.stream_url,
            '-vn',  # Skip video
            '-acodec', 'pcm_s16le',  # Convert to raw PCM
            '-ar', str(self.RATE),  # Audio rate
            '-ac', '1',  # Mono
            '-f', 'wav',  # Output format
            '-'  # Output to pipe
        ]
        
        if self.username and self.password:
            import base64
            auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            command.insert(1, '-headers')
            command.insert(2, f'Authorization: Basic {auth}\r\n')

        logger.info(f"Starting FFmpeg with command: {' '.join(command)}")
        
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8  # Large buffer
        )

    def process_audio(self):
        """Process audio data from FFmpeg"""
        process = self.start_ffmpeg()
        
        # Skip WAV header (44 bytes)
        process.stdout.read(44)
        
        logger.info("Starting audio processing loop")
        
        try:
            while self.running:
                # Read audio data
                audio_data = process.stdout.read(self.CHUNK)
                if not audio_data:
                    logger.error("No audio data received")
                    break
                
                # Calculate audio level (RMS)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                rms = np.sqrt(np.mean(np.square(audio_array)))
                db = 20 * np.log10(rms) if rms > 0 else -float('inf')
                
                # Normalize to 0-100 range
                normalized_level = max(0, min(100, (db + 80) * 1.5))
                logger.info(f"Audio Level: {normalized_level:.1f}")
                
                # Play audio
                try:
                    self.stream.write(audio_data)
                except Exception as e:
                    logger.error(f"Error playing audio: {e}")
                    
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
        finally:
            process.terminate()
            process.wait()
            logger.info("FFmpeg process terminated")

    def start(self):
        """Start monitoring"""
        self.running = True
        self.audio_thread = threading.Thread(target=self.process_audio)
        self.audio_thread.start()
        logger.info("Audio monitoring started")

    def stop(self):
        """Stop monitoring"""
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