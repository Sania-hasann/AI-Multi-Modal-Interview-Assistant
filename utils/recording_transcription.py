import os
import time
import threading
import configparser
import cv2
import pyaudio
import wave
import speech_recognition as sr

# Load config
config = configparser.ConfigParser()
config.read('config/recording_transcription_config.ini')

stop_video_event = threading.Event()

def record_video_audio(output_filename, stop_event):
    """Record video with audio using OpenCV and PyAudio."""
    cap = cv2.VideoCapture(0)  # Open webcam
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_writer = cv2.VideoWriter(output_filename, fourcc, 20.0, (640, 480))

    # Audio settings
    audio_format = pyaudio.paInt16
    channels = 1
    rate = 44100
    chunk = 1024

    audio = pyaudio.PyAudio()
    stream = audio.open(format=audio_format, channels=channels,
                        rate=rate, input=True, frames_per_buffer=chunk)
    
    audio_frames = []

    while not stop_event.is_set():
        ret, frame = cap.read()
        if ret:
            video_writer.write(frame)
        audio_frames.append(stream.read(chunk))

    # Stop recording
    cap.release()
    video_writer.release()
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save audio file
    audio_filename = "session/audio/session_audio.wav"
    with wave.open(audio_filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(audio_format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(audio_frames))

    # Merge video & audio using FFmpeg
    final_output = "session/video/interview_session_with_audio.avi"
    #ensure final_output directory exists
    os.makedirs(os.path.dirname("session/video"), exist_ok=True)
    os.system(f'ffmpeg -i "{output_filename}" -i "{audio_filename}" -c:v copy -c:a aac "{final_output}"')

    print(f"Video with audio saved as {final_output}")

def start_video_recording():
    """Start video + audio recording."""
    global stop_video_event
    stop_video_event.clear()
    video_filename = "interview_session.avi"
    video_thread = threading.Thread(target=record_video_audio, args=(video_filename, stop_video_event))
    video_thread.start()
    return video_thread

def stop_video_recording(video_thread):
    """Stop video + audio recording."""
    global stop_video_event
    stop_video_event.set()
    video_thread.join()


# **RESTORED: Per-question Audio Recording & Transcription**
def record_audio(filename, stop_event):
    """Record audio for each question separately."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Recording... Please answer the question.")
        audio_data = []
        start_time = time.time()
        max_duration = int(config['Recording']['max_duration'])

        while not stop_event.is_set() and (time.time() - start_time) < max_duration:
            try:
                audio = recognizer.listen(source, timeout=int(config['Recording']['timeout']),
                                          phrase_time_limit=int(config['Recording']['phrase_time_limit']))
                audio_data.append(audio)
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                print(f"Error occurred while listening: {e}")
                break

        if audio_data:
            with open(filename, "wb") as f:
                for segment in audio_data:
                    f.write(segment.get_wav_data())
            print(f"Recording stopped and audio saved to {filename}.")
        else:
            print("Error: No audio data recorded. Please try again.")

def transcribe_audio_speech_recognition(audio_file):
    """Transcribe recorded audio using Google Speech Recognition."""
    recognizer = sr.Recognizer()
    if not os.path.exists(audio_file):
        return "Transcription error: Audio file not found."

    attempts = 0
    max_attempts = int(config['Transcription']['max_attempts'])
    transcription = "Transcription error: Speech was unintelligible."

    while attempts < max_attempts:
        with sr.AudioFile(audio_file) as source:
            try:
                audio_data = recognizer.record(source)
                transcription = recognizer.recognize_google(audio_data)
                return transcription
            except sr.UnknownValueError:
                transcription = "Transcription error: Speech was unintelligible."
            except sr.RequestError as e:
                transcription = f"Transcription error: Request error; {e}"

        attempts += 1

    return transcription

def record_and_transcribe(filename):
    """Record per-question audio & transcribe it."""
    stop_event = threading.Event()
    recording_thread = threading.Thread(target=record_audio, args=(filename, stop_event))
    recording_thread.start()
    input("Press Enter to stop recording...")  # User stops recording manually
    stop_event.set()
    recording_thread.join()

    if os.path.exists(filename):
        print(f"Audio file {filename} successfully created.")
    else:
        print(f"Error: Audio file {filename} was not created.")
        return None

    return transcribe_audio_speech_recognition(filename)

# version two without voice video recording
# import os
# import time
# import threading
# import configparser
# import cv2
# import speech_recognition as sr

# # Load configuration
# config = configparser.ConfigParser()
# config.read('config/recording_transcription_config.ini')

# # Global variable to control video recording
# stop_video_event = threading.Event()

# def record_video(output_filename, stop_event):
#     """Records video from the webcam."""
#     cap = cv2.VideoCapture(0)  # Open webcam
#     fourcc = cv2.VideoWriter_fourcc(*'XVID')
#     video_writer = cv2.VideoWriter(output_filename, fourcc, 20.0, (640, 480))

#     while not stop_event.is_set():
#         ret, frame = cap.read()
#         if ret:
#             video_writer.write(frame)

#     cap.release()
#     video_writer.release()
#     print(f"Video recording saved as {output_filename}")

# def start_video_recording():
#     """Starts video recording when the interview begins."""
#     global stop_video_event
#     stop_video_event.clear()
#     video_filename = "interview_session.avi"
#     video_thread = threading.Thread(target=record_video, args=(video_filename, stop_video_event))
#     video_thread.start()
#     return video_thread

# def stop_video_recording(video_thread):
#     """Stops video recording after the interview ends."""
#     global stop_video_event
#     stop_video_event.set()
#     video_thread.join()

# # Function to record audio per question
# def record_audio(filename, stop_event):
#     recognizer = sr.Recognizer()
#     with sr.Microphone() as source:
#         print("Recording... Please answer the question.")
#         audio_data = []
#         start_time = time.time()
#         max_duration = int(config['Recording']['max_duration'])

#         while not stop_event.is_set() and (time.time() - start_time) < max_duration:
#             try:
#                 audio = recognizer.listen(source, timeout=int(config['Recording']['timeout']),
#                                           phrase_time_limit=int(config['Recording']['phrase_time_limit']))
#                 audio_data.append(audio)
#             except sr.WaitTimeoutError:
#                 pass
#             except Exception as e:
#                 print(f"Error occurred while listening: {e}")
#                 break

#         if audio_data:
#             with open(filename, "wb") as f:
#                 for segment in audio_data:
#                     f.write(segment.get_wav_data())
#             print(f"Recording stopped and audio saved to {filename}.")
#         else:
#             print("Error: No audio data recorded. Please try again.")

# # Function to transcribe recorded audio
# def transcribe_audio_speech_recognition(audio_file):
#     recognizer = sr.Recognizer()
#     if not os.path.exists(audio_file):
#         return "Transcription error: Audio file not found."

#     attempts = 0
#     max_attempts = int(config['Transcription']['max_attempts'])
#     transcription = "Transcription error: Speech was unintelligible."

#     while attempts < max_attempts:
#         with sr.AudioFile(audio_file) as source:
#             try:
#                 audio_data = recognizer.record(source)
#                 transcription = recognizer.recognize_google(audio_data)
#                 return transcription
#             except sr.UnknownValueError:
#                 transcription = "Transcription error: Speech was unintelligible."
#             except sr.RequestError as e:
#                 transcription = f"Transcription error: Request error; {e}"

#         attempts += 1

#     return transcription

# # Main function to record and transcribe per question
# def record_and_transcribe(filename):
#     stop_event = threading.Event()
#     recording_thread = threading.Thread(target=record_audio, args=(filename, stop_event))
#     recording_thread.start()
#     input("Press Enter to stop recording...")  # Wait for user input to stop recording
#     stop_event.set()
#     recording_thread.join()

#     if os.path.exists(filename):
#         print(f"Audio file {filename} successfully created.")
#     else:
#         print(f"Error: Audio file {filename} was not created.")
#         return None

#     return transcribe_audio_speech_recognition(filename)


#version original
# import os
# import time
# import threading
# import configparser
# import speech_recognition as sr

# # Load recording and transcription configuration
# config = configparser.ConfigParser()
# config.read('config/recording_transcription_config.ini')

# # Function to record audio continuously from the user
# def record_audio(filename, stop_event):
#     recognizer = sr.Recognizer()
#     with sr.Microphone() as source:
#         print("Recording... Please answer the question.")
#         audio_data = []
#         start_time = time.time()
#         max_duration = int(config['Recording']['max_duration'])

#         while not stop_event.is_set() and (time.time() - start_time) < max_duration:
#             try:
#                 audio = recognizer.listen(source, timeout=int(config['Recording']['timeout']), phrase_time_limit=int(config['Recording']['phrase_time_limit']))
#                 audio_data.append(audio)
#             except sr.WaitTimeoutError:
#                 pass
#             except Exception as e:
#                 print(f"Error occurred while listening: {e}")
#                 break

#         if audio_data:
#             with open(filename, "wb") as f:
#                 for segment in audio_data:
#                     f.write(segment.get_wav_data())
#             print(f"Recording stopped and audio saved to {filename}.")
#         else:
#             print("Error: No audio data recorded. Please try again.")

# # Function to transcribe audio using SpeechRecognition
# def transcribe_audio_speech_recognition(audio_file):
#     recognizer = sr.Recognizer()
#     if not os.path.exists(audio_file):
#         return "Transcription error: Audio file not found."

#     attempts = 0
#     max_attempts = int(config['Transcription']['max_attempts'])
#     transcription = "Transcription error: Speech was unintelligible."

#     while attempts < max_attempts:
#         with sr.AudioFile(audio_file) as source:
#             try:
#                 audio_data = recognizer.record(source)
#                 transcription = recognizer.recognize_google(audio_data)
#                 return transcription
#             except sr.UnknownValueError:
#                 transcription = "Transcription error: Speech was unintelligible."
#             except sr.RequestError as e:
#                 transcription = f"Transcription error: Request error; {e}"

#         attempts += 1

#     return transcription

# # Main function to handle recording and transcription
# def record_and_transcribe(filename):
#     stop_event = threading.Event()
#     recording_thread = threading.Thread(target=record_audio, args=(filename, stop_event))
#     recording_thread.start()
#     input("Press Enter to stop recording...")  # Wait for user input to stop recording
#     stop_event.set()
#     recording_thread.join()

#     if os.path.exists(filename):
#         print(f"Audio file {filename} successfully created.")
#     else:
#         print(f"Error: Audio file {filename} was not created.")
#         return None

#     attempts = 0
#     max_attempts = int(config['Transcription']['max_attempts'])
#     transcription = "Transcription error: Speech was unintelligible."

#     while transcription.startswith("Transcription error") and attempts < max_attempts:
#         transcription = transcribe_audio_speech_recognition(filename)
#         attempts += 1
#         if transcription.startswith("Transcription error"):
#             print(f"Attempt {attempts} failed. Trying again...")
#             time.sleep(5)  # Small delay before retrying
#             stop_event = threading.Event()
#             recording_thread = threading.Thread(target=record_audio, args=(filename, stop_event))
#             recording_thread.start()
#             input("Press Enter to stop recording...")  # Wait for user input to stop recording
#             stop_event.set()
#             recording_thread.join()

#     if transcription.startswith("Transcription error"):
#         print("Skipping to the next question due to repeated intelligibility issues.")
#         os.remove(filename)  # Remove the audio file if no audio was detected
#         return None
#     else:
#         return transcription