import os
import cv2
import numpy as np
from deepface import DeepFace
from mtcnn import MTCNN
import json

# Initialize MTCNN for face detection
detector = MTCNN()

def segment_video(video_path, chunk_duration_sec=3):
    """Segment video into chunks with timestamps."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames_per_chunk = int(fps * chunk_duration_sec)
    segments = []
    frame_count = 0
    current_chunk = []
    start_frame = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        current_chunk.append(frame)
        frame_count += 1
        if frame_count % frames_per_chunk == 0:
            start_sec = start_frame / fps
            end_sec = frame_count / fps
            segments.append((current_chunk, start_sec, end_sec))
            current_chunk = []
            start_frame = frame_count
    if current_chunk:
        start_sec = start_frame / fps
        end_sec = frame_count / fps
        segments.append((current_chunk, start_sec, end_sec))
    cap.release()
    return segments

def process_video_segments(segments):
    """Process video segments for emotion detection."""
    all_results = []
    for frames, start_sec, end_sec in segments:
        segment_emotions = []
        for frame in frames:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = detector.detect_faces(img_rgb)
            for face in faces:
                x, y, w, h = face['box']
                face_crop = img_rgb[y:y+h, x:x+w]
                if face_crop.size > 0:
                    try:
                        result = DeepFace.analyze(face_crop, actions=['emotion'], enforce_detection=False)
                        
                        # Filter and rename emotions
                        desired_emotions = ['angry', 'happy', 'fear', 'neutral', 'sad']
                        emotion_scores = {k: v for k, v in result[0]['emotion'].items() if k in desired_emotions}
                        emotion_scores = {('fearful' if k == 'fear' else k): v for k, v in emotion_scores.items()}

                        dominant_emotion = max(emotion_scores, key=emotion_scores.get)
                        confidence = emotion_scores[dominant_emotion]

                        segment_emotions.append({
                            'dominant_emotion': dominant_emotion,
                            'confidence': confidence,
                            'all_predictions': emotion_scores
                        })

                    except Exception as e:
                        print(f"Error processing frame: {e}")
                        continue
        if segment_emotions:
            dominant_emotion = max(segment_emotions, key=lambda x: x['confidence'])['dominant_emotion']
            avg_confidence = sum(e['confidence'] for e in segment_emotions) / len(segment_emotions)
            all_predictions = {}
            for k in segment_emotions[0]['all_predictions'].keys():
                all_predictions[k] = sum(e['all_predictions'][k] for e in segment_emotions) / len(segment_emotions)
            result_json = {
                'start_time_sec': start_sec,
                'end_time_sec': end_sec,
                'dominant_emotion': dominant_emotion,
                'confidence': avg_confidence,
                'all_predictions': all_predictions
            }
            all_results.append(result_json)
    return all_results

def get_response_video_files(directory):
    """Get MP4 files starting with 'response_'."""
    video_files = []
    for filename in os.listdir(directory):
        if filename.startswith('response_') and filename.endswith('_with_audio.mp4'):
            full_path = os.path.join(directory, filename)
            if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
                video_files.append(full_path)
    return video_files

def emotion_detection_fer():
    directory_path = r"C:\Users\uarif\OneDrive\Documents\Semester 8\cutsomfyp2\scripts"
    file_list = get_response_video_files(directory_path)

    if not file_list:
        print("No valid response MP4 files found.")
        return

    print(f"Found {len(file_list)} response files to process")

    all_file_results = []
    for video_file in file_list:
        print(f"Processing file: {video_file}")
        segments = segment_video(video_file)
        segment_results = process_video_segments(segments)
        if segment_results:
            all_file_results.append({
                'filename': video_file,
                'segments': segment_results
            })

    # Save results to JSON
    if all_file_results:
        with open("emotion_predictions_fer_multiple.json", "w") as json_file:
            json.dump(all_file_results, json_file, indent=4)
        print("JSON data saved to 'emotion_predictions_fer_multiple.json'.")
    else:
        print("No results to save.")

