import os
import json
from pydub import AudioSegment
from transformers import pipeline
import whisper

# Load local models
whisper_model = whisper.load_model("small")
ser_model = pipeline("audio-classification", model="firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3")

# Define custom emotions
CUSTOM_EMOTIONS = ["neutral", "sad", "angry", "fearful", "happy"]

def query(filename):
    try:
        results = ser_model(filename)
        # Filter results to only include custom emotions
        filtered_results = [r for r in results if r['label'] in CUSTOM_EMOTIONS]
        return filtered_results if filtered_results else None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

def segment_audio(audio_path, chunk_duration_ms=3000, min_segment_ms=1000):
    audio = AudioSegment.from_wav(audio_path)
    segments = []
    
    num_segments = len(audio) // chunk_duration_ms
    remaining_ms = len(audio) % chunk_duration_ms

    last_segment = None

    for i in range(num_segments):
        start_ms = i * chunk_duration_ms
        end_ms = start_ms + chunk_duration_ms
        segment = audio[start_ms:end_ms]
        last_segment = segment
        
        seg_path = f"session/temp/temp_audio_segment_{os.path.basename(audio_path)}_{i}.wav"
        segment.export(seg_path, format="wav")
        segments.append((seg_path, start_ms / 1000, end_ms / 1000))
    
    if remaining_ms > 0:
        start_ms = num_segments * chunk_duration_ms
        end_ms = len(audio)
        segment = audio[start_ms:end_ms]

        if len(segment) < min_segment_ms:
            if segments:
                last_path, last_start, last_end = segments.pop()
                last_audio = AudioSegment.from_wav(last_path)
                merged_audio = last_audio + segment
                merged_path = f"session/temp/temp_audio_segment_{os.path.basename(audio_path)}_{num_segments-1}_merged.wav"
                merged_audio.export(merged_path, format="wav")

                # if os.path.exists(last_path):
                #     os.remove(last_path)
                
                segments.append((merged_path, last_start, end_ms / 1000))
        else:
            seg_path = f"session/temp/temp_audio_segment_{os.path.basename(audio_path)}_{num_segments}.wav"
            segment.export(seg_path, format="wav")
            segments.append((seg_path, start_ms / 1000, end_ms / 1000))
    
    return segments

def process_audio_segments(segments):
    all_results = []
    for seg_path, start_sec, end_sec in segments:
        try:
            if not os.path.exists(seg_path):
                print(f"Segment does not exist: {seg_path}")
                continue
            # if os.path.getsize(seg_path) == 0:
            #     print(f"Empty segment file: {seg_path}")
            #     os.remove(seg_path)
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
                    print(f"Error processing predictions for {seg_path}: {e}, Output: {output}")
            else:
                print(f"No valid output for segment: {seg_path}")
        except Exception as e:
            print(f"Unexpected error processing segment {seg_path}: {str(e)}")
        # finally:
        #     if os.path.exists(seg_path):
        #         os.remove(seg_path)
    
    return all_results

def get_response_wav_files(directory):
    wav_files = []
    for filename in os.listdir(directory):
        if filename.startswith('response_') and filename.endswith('.wav'):
            full_path = os.path.join(directory, filename)
            if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
                wav_files.append(full_path)
    return wav_files

def emotion_detection_ser():
    directory_path = r"session/audio"
    file_list = get_response_wav_files(directory_path)
    
    if not file_list:
        print("No valid response WAV files found.")
        return

    print(f"Found {len(file_list)} response files to process")
    
    all_file_results = []
    for audio_file in file_list:
        try:
            print(f"Processing file: {audio_file}")
            segments = segment_audio(audio_file)
            segment_results = process_audio_segments(segments)
            if segment_results:
                all_file_results.append({
                    'filename': audio_file,
                    'segments': segment_results
                })
            else:
                print(f"No valid results for file: {audio_file}")
        except Exception as e:
            print(f"Error processing file {audio_file}: {str(e)}")
    
    if all_file_results:
        with open("session/emotion_predictions_ser_multiple.json", "w") as json_file:
            json.dump(all_file_results, json_file, indent=4)
        print("JSON data saved to 'session/emotion_predictions_ser_multiple.json'.")
    else:
        print("No results to save.")

if __name__ == "__main__":
    emotion_detection_ser()
    print("Emotion detection completed.")