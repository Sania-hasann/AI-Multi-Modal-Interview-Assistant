import os
import time
import random
import google.generativeai as genai
import re
import pyttsx3
from gtts import gTTS
from recording_transcription import record_and_transcribe
from config_loader import load_domain_config, get_subdomains
from context_awareness import parse_transcription, extract_topics, sentiment_score
from txt_to_csv import convert_txt_to_csv
from recording_transcription import start_video_recording, stop_video_recording
import scoring
import SER
import gen_report
import dotenv
import cv2
import numpy as np
from deepface import DeepFace
from mtcnn import MTCNN
import json
import threading

dotenv.load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "max_output_tokens": 500,
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)

engine = pyttsx3.init()
detector = MTCNN()

def speak(text):
    engine.say(text)
    engine.runAndWait()

def format_topics(topics):
    return ', '.join([word.split('*')[1].replace('"', '').strip() for word in topics.split('+')])

def perform_fer(frame):
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = detector.detect_faces(img_rgb)
    emotions = []
    for face in faces:
        x, y, w, h = face['box']
        face_crop = img_rgb[y:y+h, x:x+w]
        if face_crop.size > 0:
            try:
                result = DeepFace.analyze(face_crop, actions=['emotion'], enforce_detection=False)
                emotions.append(result[0]['emotion'])
            except:
                pass
    return emotions

def record_fer(stop_event, output_file, question_idx):
    cap = cv2.VideoCapture(0)
    emotion_data = []
    start_time = time.time()
    while not stop_event.is_set() and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        emotions = perform_fer(frame)
        if emotions:
            emotion_data.append({
                "timestamp": time.time() - start_time,
                "emotions": emotions[0]
            })
    cap.release()
    with open(output_file, 'w') as f:
        json.dump(emotion_data, f)
    return emotion_data

def enhanced_record_and_transcribe(filename, current_question, question_idx):
    stop_event = threading.Event()
    fer_output = f"fer_response_{question_idx}.json"
    fer_thread = threading.Thread(target=record_fer, args=(stop_event, fer_output, question_idx))
    fer_thread.start()
    
    transcription = record_and_transcribe(filename)
    
    stop_event.set()
    fer_thread.join()
    
    if transcription:
        parsed_data = parse_transcription(transcription)
        topics = extract_topics(transcription)
        sentiment = sentiment_score(transcription)
        formatted_topics = format_topics(topics[0] if topics else "")
        with open("session_history.txt", "a") as file:
            file.write(f"Question: \"{current_question}\"\n")
            file.write(f"Answer: \"{transcription}\"\n")
            file.write(f"Topics: {formatted_topics}\n")
            file.write(f"Sentiment: {sentiment}\n")
            file.write(f"FER_Output: {fer_output}\n\n")
        return transcription, topics, sentiment, fer_output
    return transcription, None, None, fer_output

def generate_questions(prompt, subdomain, domain_details, context=None, follow_up=False, question_type=None, asked_questions=[], topics=None):
    chat_session = model.start_chat(history=[])
    if follow_up and context:
        full_prompt = f"Based on the candidate's response '{context}', generate a detailed follow-up question in {subdomain} to dive deeper. Please ensure your response is phrased as a question."
    else:
        full_prompt = f"{domain_details['llm_guidance']}\n{prompt}\nGenerate a new question specifically in question form to assess knowledge in {subdomain}."
        if question_type:
            full_prompt += f"\nThe question should be of type: {question_type}"
            if topics and question_type in topics:
                full_prompt += f"\nSpecific topics to cover: {topics[question_type]}"
    response = chat_session.send_message(full_prompt)
    if response.text:
        questions = [q.strip() for q in response.text.split('\n') if q.strip() and not q.startswith("#")]
        for question in questions:
            if question.endswith('?') and question not in asked_questions:
                return question
        retry_prompt = f"{full_prompt}\nPlease make sure the response is a direct question."
        response = chat_session.send_message(retry_prompt)
        if response.text:
            questions = [q.strip() for q in response.text.split('\n') if q.strip() and not q.startswith("#")]
            for question in questions:
                if question.endswith('?') and question not in asked_questions:
                    return question
        else:
            raise Exception("Failed to generate a question after retry.")
    else:
        raise Exception("Failed to generate questions.")

def should_follow_up(response):
    keywords = ['experience', 'approach', 'method', 'challenge', 'solution', 'details', 'job', 'internship', 
                'project', 'problem', 'implementation', 'design', 'optimization', 'tool', 'process', 'framework']
    return any(re.search(rf"\b{kw}\b", response, re.IGNORECASE) for kw in keywords)

def fuse_emotions(fer_file, ser_file, fer_weight=0.6, ser_weight=0.4):
    with open(fer_file, 'r') as f:
        fer_data = json.load(f)
    with open(ser_file, 'r') as f:
        ser_data = json.load(f)
    
    fused_emotions = {}
    emotions = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
    
    if fer_data and ser_data:
        fer_avg = {emotion: 0 for emotion in emotions}
        count = 0
        for entry in fer_data:
            for emotion in emotions:
                fer_avg[emotion] += entry['emotions'].get(emotion, 0)
            count += 1
        if count > 0:
            fer_avg = {k: v / count for k, v in fer_avg.items()}
        
        ser_emotions = ser_data[0].get('emotion_probabilities', {})
        
        for emotion in emotions:
            fused_emotions[emotion] = (fer_weight * fer_avg.get(emotion, 0) + 
                                    ser_weight * ser_emotions.get(emotion, 0))
    
    return fused_emotions

def combine_scores():
    with open("evaluation_results.json", 'r') as f:
        answer_scores = json.load(f)
    with open("emotion_predictions_multiple.json", 'r') as f:
        ser_scores = json.load(f)
    
    combined_results = []
    for idx, answer in enumerate(answer_scores):
        fer_file = f"fer_response_{idx+1}.json"
        ser_file = "emotion_predictions_multiple.json"
        fused_emotions = fuse_emotions(fer_file, ser_file)
        
        combined_results.append({
            "question": answer["question"],
            "answer": answer["answer"],
            "answer_score": answer["score"],
            "fused_emotions": fused_emotions
        })
    
    with open("combined_results.json", 'w') as f:
        json.dump(combined_results, f, indent=2)

def conduct_interview():
    session_history_path = "session_history.txt"
    with open(session_history_path, "w") as file:
        file.write("")
    
    subdomains = get_subdomains()
    print("Please select the subdomain you want to be interviewed in:")
    for idx, domain in enumerate(subdomains, 1):
        print(f"{idx}. {domain}")
    
    try:
        selected_idx = int(input("Enter the number of the subdomain: ")) - 1
        selected_subdomain = subdomains[selected_idx]
    except ValueError as e:
        print(f"Error: {e}. Please select a valid number.")
        exit(1)
    
    video_thread = start_video_recording()
    
    try:
        subdomain_file = f"{selected_subdomain.replace(' ', '_').lower()}.txt"
        domain_details, intro_prompt, question_distribution, topics = load_domain_config(subdomain_file)
        
        prompt = f"You are conducting an interview for a role in {selected_subdomain}."
        context = None
        asked_questions = []
        total_questions = 2
        
        question_counts = {key: round(total_questions * (value / 100)) for key, value in question_distribution.items()}
        while sum(question_counts.values()) < total_questions:
            for key in question_counts:
                if question_counts[key] < total_questions * (question_distribution[key] / 100):
                    question_counts[key] += 1
                    break
        
        first_question = generate_questions(intro_prompt, selected_subdomain, domain_details, topics=topics)
        question = first_question
        
        for i in range(total_questions):
            if i == 0:
                print(f"Q1: {question}")
                speak(question)
            else:
                question_type = random.choices(list(question_counts.keys()), weights=list(question_counts.values()))[0]
                question_counts[question_type] -= 1
                if context and should_follow_up(context):
                    question = generate_questions(prompt, selected_subdomain, domain_details, context=context, follow_up=True, asked_questions=asked_questions, topics=topics)
                else:
                    question = generate_questions(prompt, selected_subdomain, domain_details, question_type=question_type, asked_questions=asked_questions, topics=topics)
                print(f"\n--- {question_type.upper()} QUESTION ---")
                print(f"Q{i+1}: {question}")
                speak(question)
            
            print("You have 10 seconds to understand the question...")
            time.sleep(1)
            
            audio_file = os.path.abspath(f"response_{selected_subdomain}_{i+1}.wav")
            transcription, topics, sentiment, fer_output = enhanced_record_and_transcribe(audio_file, question, i+1)
            
            if transcription and not transcription.startswith("Transcription error"):
                print(f"Answer {i+1}: {transcription}")
                context = transcription
            else:
                context = "No answer provided due to transcription error."
            
            asked_questions.append(question)
        
        convert_txt_to_csv(session_history_path, "session_history.csv")
        scoring.evaluate_answers_and_save()
        SER.sentiment()
        combine_scores()
        gen_report.generate_report("combined_results.json", "emotion_predictions_multiple.json")
        
        print("Interview complete!")
    
    finally:
        stop_video_recording(video_thread)

if __name__ == "__main__":
    conduct_interview()