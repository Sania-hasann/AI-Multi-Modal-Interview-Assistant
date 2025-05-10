import os
import requests
import json
from pydub import AudioSegment

API_URL = "https://api-inference.huggingface.co/models/firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3"
headers = {"Authorization": "Bearer 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"}

def query(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    # Specify content type based on file extension
    content_type = "audio/wav" if filename.lower().endswith('.wav') else "audio/wav"
    
    # Add Content-Type header
    request_headers = headers.copy()
    request_headers["Content-Type"] = content_type
    
    try:
        response = requests.post(API_URL, headers=request_headers, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

def segment_audio(audio_path, chunk_duration_ms=3000):
    """Segment audio into chunks with timestamps."""
    audio = AudioSegment.from_wav(audio_path)
    segments = []
    for i in range(0, len(audio), chunk_duration_ms):
        start_ms = i
        end_ms = min(i + chunk_duration_ms, len(audio))
        segment = audio[start_ms:end_ms]
        seg_path = f"temp_audio_segment_{os.path.basename(audio_path)}_{i//1000}.wav"
        segment.export(seg_path, format="wav")
        segments.append((seg_path, start_ms/1000, end_ms/1000))  # (path, start_sec, end_sec)
    return segments

def process_audio_segments(segments):
    """Process audio segments and return emotions with timestamps."""
    all_results = []
    for seg_path, start_sec, end_sec in segments:
        if not os.path.exists(seg_path) or os.path.getsize(seg_path) == 0:
            print(f"Invalid segment: {seg_path}")
            continue
        
        output = query(seg_path)
        if output:
            try:
                dominant_emotion = sorted(output, key=lambda x: x['score'], reverse=True)[0]
                result_json = {
                    'segment_filename': seg_path,
                    'start_time_sec': start_sec,
                    'end_time_sec': end_sec,
                    'dominant_emotion': dominant_emotion['label'],
                    'confidence': dominant_emotion['score'],
                    'all_predictions': output
                }
                all_results.append(result_json)
            except (KeyError, IndexError, TypeError) as e:
                print(f"Error processing {seg_path}: {e}, Output: {output}")
            finally:
                if os.path.exists(seg_path):
                    os.remove(seg_path)  # Clean up
        else:
            print(f"Error processing {seg_path}")
    
    return all_results

def get_response_wav_files(directory):
    """Get WAV files starting with 'response_'."""
    wav_files = []
    for filename in os.listdir(directory):
        if filename.startswith('response_') and filename.endswith('.wav'):
            full_path = os.path.join(directory, filename)
            if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
                wav_files.append(full_path)
    return wav_files

def emotion_detection_ser():
    directory_path = r"C:\Users\uarif\OneDrive\Documents\Semester 8\cutsomfyp2\scripts"
    file_list = get_response_wav_files(directory_path)
    
    if not file_list:
        print("No valid response WAV files found.")
        return

    print(f"Found {len(file_list)} response files to process")
    
    all_file_results = []
    for audio_file in file_list:
        print(f"Processing file: {audio_file}")
        segments = segment_audio(audio_file)
        segment_results = process_audio_segments(segments)
        if segment_results:
            all_file_results.append({
                'filename': audio_file,
                'segments': segment_results
            })
    
    # Save results to JSON
    if all_file_results:
        with open("emotion_predictions_ser_multiple.json", "w") as json_file:
            json.dump(all_file_results, json_file, indent=4)
        print("JSON data saved to 'emotion_predictions_multiple.json'.")
    else:
        print("No results to save.")

if __name__ == "__main__":
    emotion_detection_ser()