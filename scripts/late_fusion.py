import json
import os
from collections import Counter

def load_json(file_path):
    """Load JSON file."""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return []
    with open(file_path, 'r') as f:
        return json.load(f)

def align_segments(ser_segments, fer_segments):
    """Align SER and FER segments by timestamps."""
    aligned = []
    for ser_seg in ser_segments:
        ser_start = ser_seg['start_time_sec']
        ser_end = ser_seg['end_time_sec']
        # Find matching FER segment (within 0.1s tolerance)
        matching_fer = None
        for fer_seg in fer_segments:
            fer_start = fer_seg['start_time_sec']
            fer_end = fer_seg['end_time_sec']
            if abs(ser_start - fer_start) < 0.1 and abs(ser_end - fer_end) < 0.1:
                matching_fer = fer_seg
                break
        aligned.append((ser_seg, matching_fer))
    return aligned

def list_to_dict(preds):
    """Convert prediction list to dict if needed."""
    if isinstance(preds, dict):
        return preds
    elif isinstance(preds, list):
        return {item['label']: item['score'] for item in preds if 'label' in item and 'score' in item}
    return {}

def fuse_emotions(ser_seg, fer_seg, ser_weight=0.3, fer_weight=0.7):
    """Fuse emotions for a single segment using weighted averaging."""
    ser_preds = list_to_dict(ser_seg.get('all_predictions', {}))
    
    if not fer_seg:
        # Use SER only if FER is missing
        return {
            'start_time_sec': ser_seg['start_time_sec'],
            'end_time_sec': ser_seg['end_time_sec'],
            'dominant_emotion': ser_seg['dominant_emotion'],
            'confidence': ser_seg['confidence'],
            'source': 'SER_only'
        }

    fer_preds = list_to_dict(fer_seg.get('all_predictions', {}))

    # Weighted averaging of emotion probabilities
    fused_predictions = {}
    all_emotions = set(ser_preds.keys()).union(fer_preds.keys())
    for emotion in all_emotions:
        ser_score = ser_preds.get(emotion, 0) * ser_weight
        fer_score = fer_preds.get(emotion, 0) * fer_weight
        fused_predictions[emotion] = ser_score + fer_score

    # Find dominant emotion
    dominant_emotion = max(fused_predictions.items(), key=lambda x: x[1])[0]
    confidence = fused_predictions[dominant_emotion]

    return {
        'start_time_sec': ser_seg['start_time_sec'],
        'end_time_sec': ser_seg['end_time_sec'],
        'dominant_emotion': dominant_emotion,
        'confidence': confidence,
        'fused_predictions': fused_predictions,
        'source': 'SER+FER'
    }

def late_fusion(ser_data, fer_data, ser_weight=0.3, fer_weight=0.7):
    """Perform late fusion on SER and FER JSON data."""
    fused_results = []

    for ser_file in ser_data:
        ser_filename = ser_file['filename']
        base_name = os.path.splitext(os.path.basename(ser_filename))[0]
        fer_filename = f"{base_name}_with_audio_with_audio.mp4"  # Adjust this logic if needed

        # Find matching FER file
        fer_file = next((f for f in fer_data if os.path.basename(f['filename']) == fer_filename), None)

        if not fer_file:
            print(f"No matching FER file for {ser_filename}")
            fused_results.append({
                'filename': ser_filename,
                'segments': [{
                    'start_time_sec': seg['start_time_sec'],
                    'end_time_sec': seg['end_time_sec'],
                    'dominant_emotion': seg['dominant_emotion'],
                    'confidence': seg['confidence'],
                    'source': 'SER_only'
                } for seg in ser_file['segments']]
            })
            continue

        aligned_segments = align_segments(ser_file['segments'], fer_file['segments'])
        fused_segments = [fuse_emotions(ser_seg, fer_seg, ser_weight, fer_weight) for ser_seg, fer_seg in aligned_segments]

        fused_results.append({
            'filename': ser_filename,
            'segments': fused_segments
        })

    return fused_results

def aggregate_fused_emotions(fused_results):
    """Aggregate dominant emotions for each file."""
    aggregated = []
    for file_result in fused_results:
        emotions = [seg['dominant_emotion'] for seg in file_result['segments']]
        dominant_emotion = Counter(emotions).most_common(1)[0][0] if emotions else "neutral"
        aggregated.append({
            'filename': file_result['filename'],
            'dominant_emotion': dominant_emotion,
            'segments': file_result['segments']
        })
    return aggregated

def main():
    # Load JSON files
    ser_data = load_json("emotion_predictions_ser_multiple.json")
    fer_data = load_json("emotion_predictions_fer_multiple.json")

    # Perform late fusion
    fused_results = late_fusion(ser_data, fer_data, ser_weight=0.3, fer_weight=0.7)

    # Aggregate overall emotion per file
    aggregated_results = aggregate_fused_emotions(fused_results)

    # Save results
    with open("fused_emotion_predictions.json", "w") as f:
        json.dump(aggregated_results, f, indent=4)
    print("✅ Fused emotion predictions saved to 'fused_emotion_predictions.json'.")

if __name__ == "__main__":
    main()
