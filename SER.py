import os
import requests
import json

API_URL = "https://api-inference.huggingface.co/models/firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3"
headers = {"Authorization": "Bearer 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"}

def query(filename):
    with open(filename, "rb") as f:
        data = f.read()
    response = requests.post(API_URL, headers=headers, data=data)

    # Check if the response was successful
    if response.status_code == 200:
        return response.json()  # Return the JSON response if successful
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def process_multiple_files(file_list):
    all_results = []  # List to store results for all audio files
    for filename in file_list:
        print(f"Processing file: {filename}")
        output = query(filename)
        if output:
            # Extract dominant emotion for each file and add to results
            dominant_emotion = sorted(output, key=lambda x: x['score'], reverse=True)[0]
            result_json = {
                'filename': filename,
                'dominant_emotion': dominant_emotion['label'],
                'confidence': dominant_emotion['score'],
                'all_predictions': output
            }
            all_results.append(result_json)  # Add result for this file to the list
        else:
            print(f"Error processing {filename}")
    
    return all_results

def get_wav_files_from_directory(directory):
    wav_files = []
    for filename in os.listdir(directory):
        if filename.endswith('.wav'):
            wav_files.append(os.path.join(directory, filename))
    return wav_files

# Specify the directory containing .wav files
def sentiment():
    directory_path = r"audio-llm-SER-video"

    # Get list of .wav files from the directory
    file_list = get_wav_files_from_directory(directory_path)

    # Process the files and save the results
    results = process_multiple_files(file_list)

    # Save the results to a JSON file
    if results:
        with open("emotion_predictions_multiple.json", "w") as json_file:
            json.dump(results, json_file, indent=4)

        print("JSON data has been saved to 'emotion_predictions_multiple.json'.")
    else:
        print("No results to save.")
    
