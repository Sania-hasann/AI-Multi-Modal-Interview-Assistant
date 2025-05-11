import os
import time
import random
import google.generativeai as genai
import re
import pyttsx3
import subprocess
import signal
from pydub import AudioSegment
from transformers import pipeline
from recording_transcription import record_and_transcribe
from config_loader import load_domain_config, get_subdomains
from context_awareness import parse_transcription, extract_topics, sentiment_score
from FER import emotion_detection_fer
from SER import emotion_detection_ser
from late_fusion import fusion
from report import generate_report
from txt_to_csv import convert_txt_to_csv
import scoring
import dotenv
import report_generation

dotenv.load_dotenv()

# Set up Google Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize model configuration
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "max_output_tokens": 500,
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)

# Initialize the text-to-speech engine
engine = pyttsx3.init()

def speak(text):
    """Speak out the text using an offline engine."""
    engine.say(text)
    engine.runAndWait()

def format_topics(topics):
    # Extract words from the string of topics, assuming the format "0.059*'model' + 0.044*'speech' + ..."
    return ', '.join([word.split('*')[1].replace('"', '').strip() for word in topics.split('+')])

# Video and audio recording parameters
RATE = 44100
VIDEO_FPS = 20
VIDEO_SIZE = "640x480"

def enhanced_record_and_transcribe(video_filename, audio_filename, current_question):
    """Record video/audio, extract audio, transcribe, and perform NLP tasks."""
    # Record video and audio, then transcribe
    transcription = record_and_transcribe(video_filename, audio_filename)
    
    if transcription and not transcription.startswith("Transcription error"):
        # Perform NLP tasks
        parsed_data = parse_transcription(transcription)
        topics = extract_topics(transcription)
        sentiment = sentiment_score(transcription)

        # Format topics for better readability
        formatted_topics = format_topics(topics[0] if topics else "")

        # Save session data
        with open("session/session_history.txt", "a") as file:
            file.write(f"Question: \"{current_question}\"\n")
            file.write(f"Answer: \"{transcription}\"\n")
            file.write(f"Topics: {formatted_topics}\n")
            file.write(f"Sentiment: {sentiment}\n")
            file.write(f"Video: {video_filename}\n")
            file.write(f"Audio: {audio_filename}\n\n")

        return transcription, topics, sentiment, parsed_data

    return transcription, None, None, None

# Function to generate interview questions
def generate_questions(prompt, subdomain, domain_details, context=None, follow_up=False, question_type=None, asked_questions=[], topics=None):
    chat_session = model.start_chat(history=[])

    # Determine prompt based on follow-up or new question
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
        # Split response by lines, removing any empty lines or comments
        questions = [q.strip() for q in response.text.split('\n') if q.strip() and not q.startswith("#")]

        # Ensure at least one line is phrased as a question
        for question in questions:
            if question.endswith('?') and question not in asked_questions:
                return question  # Return the first valid question found

        # Retry if no question is generated
        retry_prompt = f"{full_prompt}\nPlease make sure the response is a direct question."
        response = chat_session.send_message(retry_prompt)

        # Recheck the response for a question
        if response.text:
            questions = [q.strip() for q in response.text.split('\n') if q.strip() and not q.startswith("#")]
            for question in questions:
                if question.endswith('?') and question not in asked_questions:
                    return question
        else:
            raise Exception("Failed to generate a question after retry.")
    else:
        raise Exception("Failed to generate questions.")

# Function to check if the response is detailed enough for a follow-up question
def should_follow_up(response):
    keywords = ['experience', 'approach', 'method', 'challenge', 'solution', 'details', 'job', 'internship', 
                'project', 'problem', 'implementation', 'design', 'optimization', 'tool', 'process', 'framework']
    return any(re.search(rf"\b{kw}\b", response, re.IGNORECASE) for kw in keywords)

# Main function to conduct the interview
def conduct_interview():
    # File path for the session history
    session_history_path = "session/session_history.txt"

    # Open the file in write mode ('w') to overwrite old content or create a new one if it doesn't exist
    with open(session_history_path, "w") as file:
        file.write("")

    # Load subdomains
    subdomains = get_subdomains()
    
    # Select subdomain
    print("Please select the subdomain you want to be interviewed in:")
    for idx, domain in enumerate(subdomains, 1):
        print(f"{idx}. {domain}")
    
    selected_idx = int(input("Enter the number of the subdomain: ")) - 1
    selected_subdomain = subdomains[selected_idx]

    # Load domain details, intro prompt, first question, question distribution, and topics
    subdomain_file = f"{selected_subdomain.replace(' ', '_').lower()}.txt"
    domain_details, intro_prompt, question_distribution, topics = load_domain_config(subdomain_file)

    # Initialize prompt and context
    prompt = f"You are conducting an interview for a role in {selected_subdomain}."
    context = None
    asked_questions = []

    # Calculate the number of questions for each type
    total_questions = 1  # Example total number of questions
    question_counts = {key: round(total_questions * (value / 100)) for key, value in question_distribution.items()}

    # Ensure the total number of questions is correct
    while sum(question_counts.values()) < total_questions:
        for key in question_counts:
            if question_counts[key] < total_questions * (question_distribution[key] / 100):
                question_counts[key] += 1
                break

    # Start the interview with the first question
    first_question = generate_questions(intro_prompt, selected_subdomain, domain_details, topics=topics)
    question = first_question

    for i in range(total_questions):
        if i == 0:
            # Use the predefined first question for the first round
            print(f"Q1: {question}")
            speak(question)
        else:
            # Determine the type of question to generate
            question_type = random.choices(list(question_counts.keys()), weights=list(question_counts.values()))[0]
            question_counts[question_type] -= 1

            # Generate a follow-up or new question based on context
            if context and should_follow_up(context):
                question = generate_questions(prompt, selected_subdomain, domain_details, context=context, follow_up=True, asked_questions=asked_questions, topics=topics)
            else:
                question = generate_questions(prompt, selected_subdomain, domain_details, question_type=question_type, asked_questions=asked_questions, topics=topics)

            # Print the question type heading before the question
            print(f"\n--- {question_type.upper()} QUESTION ---")
            print(f"Q{i+1}: {question}")
            speak(question)

        # Wait for a short time for user to read the question
        print("You have 10 seconds to understand the question...")
        time.sleep(1)

        # Define video and audio file paths
        video_file = os.path.abspath(f"session/response_{selected_subdomain}_{i+1}_with_audio.mp4")
        audio_file = os.path.abspath(f"session/response_{selected_subdomain}_{i+1}.wav")
        transcription, topics, sentiment, parsed_data = enhanced_record_and_transcribe(video_file, audio_file, question)

        question_sentiments = {}

        if transcription and not transcription.startswith("Transcription error"):
            context = transcription
            question_number = i + 1
            question_sentiments[f"Q{question_number}"] = sentiment
        else:
            context = "No answer provided due to transcription error."
            question_number = i + 1
            question_sentiments[f"Q{question_number}"] = "N/A"

        # Add the asked question to the list
        asked_questions.append(question)

    convert_txt_to_csv(session_history_path, "session_history.csv")
    scoring.evaluate_answers_and_save()
    emotion_detection_ser()
    emotion_detection_fer()
    fusion()
    generate_report("session/evaluation_results.json", "session/fused_emotion_predictions.json")

if __name__ == "__main__":
    conduct_interview()