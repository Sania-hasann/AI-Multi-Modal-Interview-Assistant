import os
import subprocess
import signal
import time
from pydub import AudioSegment
from transformers import pipeline

# Recording parameters
RATE = 44100
VIDEO_FPS = 20
VIDEO_SIZE = "640x480"

token = os.getenv("HF_TOKEN")
print(f"Token: {token}")
def record_video_audio(video_filename):
    """Record video and audio using hardcoded working device names."""
    # Only create directory if path includes a folder
    video_dir = os.path.dirname(video_filename)
    if video_dir:
        os.makedirs(video_dir, exist_ok=True)

    # Hardcoded device names (replace if needed)
    raw_video_line = '"Integrated Camera" (video)'
    raw_audio_line = '"Microphone Array (AMD Audio Device)" (audio)'

    def extract_device_name(raw_line):
        start = raw_line.find('"') + 1
        end = raw_line.rfind('"')
        return raw_line[start:end]

    video_device = extract_device_name(raw_video_line)
    audio_device = extract_device_name(raw_audio_line)

    command = [
        'ffmpeg', '-y',
        '-f', 'dshow',
        '-i', f'video={video_device}:audio={audio_device}',
        '-vcodec', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'veryfast',
        '-crf', '23',
        '-r', str(VIDEO_FPS),
        '-s', VIDEO_SIZE,
        '-acodec', 'aac',
        '-ar', str(RATE),
        '-ac', '1',
        video_filename
    ]

    print(f"🎥 Starting recording with:\nVideo: {video_device}\nAudio: {audio_device}")
    print("⏺️ Press Enter to stop recording...")

    try:
        process = subprocess.Popen(
            command,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )

        input()  # Wait for Enter
        process.send_signal(signal.CTRL_BREAK_EVENT)
        process.wait(timeout=5)

        print("✅ Recording complete.")
        return os.path.exists(video_filename)
    except Exception as e:
        print(f"❌ Recording failed: {e}")
        return False


def extract_audio(video_filename, audio_filename):
    """Extract audio from video as WAV using FFmpeg."""
    try:
        audio_dir = os.path.dirname(audio_filename)
        if audio_dir:
            os.makedirs(audio_dir, exist_ok=True)

        command = [
            'ffmpeg', '-y',
            '-i', video_filename,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', str(RATE),
            '-ac', '1',
            audio_filename
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Audio extracted to {audio_filename}")
        print(f"FFmpeg output: {result.stdout}")

        audio = AudioSegment.from_wav(audio_filename)
        audio_duration = len(audio) / 1000.0
        print(f"Audio duration: {audio_duration:.2f} seconds")
        return audio_duration
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")
        return 0


def transcribe_audio(audio_filename):
    """Transcribe audio using Whisper."""
    try:
        audio = AudioSegment.from_wav(audio_filename)
        if len(audio) < 1000:
            return "Transcription error: Audio too short."
        
        transcriber = pipeline("automatic-speech-recognition", model="openai/whisper-small",token=token)
        result = transcriber(audio_filename)
        return result["text"]
    except Exception as e:
        print(f"Transcription error: {e}")
        return "Transcription error"

def record_and_transcribe(video_filename, audio_filename):
    """Record video/audio, extract audio, and transcribe."""
    # Record video with audio
    if not record_video_audio(video_filename):
        return "Transcription error: Recording failed"
    
    # Extract audio
    audio_duration = extract_audio(video_filename, audio_filename)
    if audio_duration == 0:
        print(f"Error: Audio file {audio_filename} was not created.")
        return "Transcription error: No audio extracted"
    
    # Verify video duration
    try:
        command = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_filename
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        video_duration = float(result.stdout.strip())
        print(f"Video duration: {video_duration:.2f} seconds")
        
        if abs(video_duration - audio_duration) > 0.5:
            print(f"Warning: Audio duration ({audio_duration:.2f}s) and video duration ({video_duration:.2f}s) differ.")
    except subprocess.CalledProcessError as e:
        print(f"FFprobe error: {e.stderr}")
    
    # Rename video file to match expected output
    output_filename = video_filename.replace('.mp4', '_with_audio.mp4')
    os.rename(video_filename, output_filename)
    print(f"Renamed video to {output_filename}")
    
    # Transcribe audio
    transcription = transcribe_audio(audio_filename)
    
    return transcription


