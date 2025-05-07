import json
import os

def extract_scores(feedback):
    # Assuming scores are in the format "Accuracy Score: X/10"
    accuracy = int(feedback.split("Accuracy Score: ")[1].split("/")[0])
    preciseness = int(feedback.split("Preciseness Score: ")[1].split("/")[0])
    clarity = int(feedback.split("Clarity Score: ")[1].split("/")[0])
    return accuracy, preciseness, clarity

def parse_evaluation_json(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    new_data = {
        "questions": [],
        "stackedBarChartData": {
            "labels": [],
            "datasets": [
                {"label": "Accuracy", "data": []},
                {"label": "Preciseness", "data": []},
                {"label": "Clarity", "data": []}
            ]
        }
    }

    for i, question_data in enumerate(data):
        question, answer, feedback = question_data
        new_data["questions"].append({
            "question": question,
            "answer": answer,
            "feedback": feedback
        })

        # Extract scores from feedback
        accuracy, clarity, preciseness = extract_scores(feedback)
        new_data["stackedBarChartData"]["labels"].append(f"Q{i+1}")
        new_data["stackedBarChartData"]["datasets"][0]["data"].append(accuracy)
        new_data["stackedBarChartData"]["datasets"][1]["data"].append(preciseness)
        new_data["stackedBarChartData"]["datasets"][2]["data"].append(clarity)

    return new_data

def parse_emotion_json(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    bar_chart_data = {
        "labels": [],
        "scores": [],
        "colors": []
    }
    emotion_colors = {
            "neutral": "rgba(150, 150, 150, 0.65)", # Darker Gray for neutral
            "angry": "rgba(220, 0, 0, 0.65)",        # Darker Red for anger
            "sad": "rgba(0, 0, 200, 0.65)",          # Darker Blue for sadness
            "fearful": "rgba(220, 140, 0, 0.65)",    # Darker Orange for fear
            "surprised": "rgba(255, 220, 0, 0.65)",  # Darker Yellow for surprise
            "disgust": "rgba(180, 0, 180, 0.65)"     # Darker Purple for disgust
        }
    for item in data:
        bar_chart_data["labels"].append(item["dominant_emotion"])
        bar_chart_data["scores"].append(item["confidence"])
        bar_chart_data["colors"].append(emotion_colors[item["dominant_emotion"]])
    return bar_chart_data

def generate_report(evaluation_json_file, emotion_json_file):
    # Verify json files exist
    try:
        with open(evaluation_json_file, 'r') as f:
            pass
    except FileNotFoundError:
        print(f"Error: {evaluation_json_file} not found.")
        return
        
    try:
        with open(emotion_json_file, 'r') as f:
            pass
    except FileNotFoundError:
        print(f"Error: {emotion_json_file} not found.")
        return
    
    # Ensure report directory exists
    os.makedirs("report", exist_ok=True)
    
    data = parse_evaluation_json(evaluation_json_file)
    emotion_data = parse_emotion_json(emotion_json_file)

    data["barChartData"] = emotion_data

    # HTML Template with Placeholder
    # [rest of your HTML template code remains the same]


if __name__ == "__main__":
    generate_report("evaluation_results.json", "emotion_predictions_multiple.json")