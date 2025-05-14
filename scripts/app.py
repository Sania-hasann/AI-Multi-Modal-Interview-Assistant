import os
import time
import random
import streamlit as st
import pyttsx3
from config_loader import load_domain_config, get_subdomains
from recording_transcription import record_and_transcribe
from report import generate_report
from main import generate_questions,should_follow_up
from resume_data import extract_resume_info, save_resume_data
from FER import emotion_detection_fer
from SER import emotion_detection_ser
from late_fusion import fusion
import scoring
import google.generativeai as genai
import re

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

# Initialize text-to-speech engine
engine = pyttsx3.init()

def speak(text):
    """Speak out the text using an offline engine."""
    engine.say(text)
    engine.runAndWait()

# Video and audio recording parameters
RATE = 44100
VIDEO_FPS = 20
VIDEO_SIZE = "640x480"

# Streamlit Welcome Screen
st.title("AI-Driven Interview Bot")
st.subheader("Welcome to the Interview Bot. Please follow the instructions below.")

# Resume Upload
uploaded_file = st.file_uploader("Upload your resume (PDF format)", type=["pdf"])
if uploaded_file:
    resume_data = extract_resume_info(uploaded_file)
    save_resume_data(resume_data)
    st.write("Resume uploaded successfully. The system will generate personalized interview questions based on your resume.")

    # Subdomain Selection
    subdomains = get_subdomains()
    selected_subdomain = st.selectbox("Select Subdomain for Interview", subdomains)

    # Number of Questions
    num_questions = st.number_input("How many questions would you like to attempt?", min_value=1, step=1)

    # Interview Process
    if st.button("Start Interview"):
        st.write("Starting the interview...")
        session_history = []

        # Load the domain config for the selected subdomain
        subdomain_file = f"{selected_subdomain.replace(' ', '_').lower()}.txt"
        domain_details, intro_prompt, question_distribution, topics = load_domain_config(subdomain_file)

        total_questions = num_questions
        question_counts = {key: round(total_questions * (value / 100)) for key, value in question_distribution.items()}
        
        while sum(question_counts.values()) < total_questions:
            for key in question_counts:
                if question_counts[key] < total_questions * (question_distribution[key] / 100):
                    question_counts[key] += 1
                    break

        for i in range(total_questions):
            if i == 0:
                question = generate_questions(intro_prompt, selected_subdomain, domain_details, topics=topics, resume_data=resume_data)
                st.write(f"*Q{i+1}:* {question}")
                speak(question)
            else:
                question_type = random.choices(list(question_counts.keys()), weights=list(question_counts.values()))[0]
                question_counts[question_type] -= 1
                context = session_history[-1] if session_history else None
                question = generate_questions(
                    intro_prompt, selected_subdomain, domain_details, context=context,
                    follow_up=bool(context and should_follow_up(context)),
                    question_type=question_type, topics=topics, resume_data=resume_data
                )
                st.write(f"*Q{i+1}:* {question}")
                speak(question)

            st.write("You have 10 seconds to understand the question...")
            time.sleep(1)

            # Start recording audio and video
            video_file = os.path.abspath(f"response_{selected_subdomain}_{i+1}_with_audio.mp4")
            audio_file = os.path.abspath(f"response_{selected_subdomain}_{i+1}.wav")
            transcription, topics, sentiment, parsed_data = record_and_transcribe(video_file, audio_file, question)

            if transcription and not transcription.startswith("Transcription error"):
                session_history.append(transcription)
            else:
                session_history.append("No answer provided due to transcription error.")

            # Evaluate answers and save
            scoring.evaluate_answers_and_save()

        # Post Interview Actions: Show Results and Download Option
        st.write("Interview completed. Would you like to view the results?")
        if st.button("View Results"):
            generate_report("evaluation_results.json", "fused_emotion_predictions.json")
            st.write("The report has been generated. You can download it below.")
            st.download_button("Download Report", "evaluation_results.html")

        # Emotion Detection
        emotion_detection_ser()
        emotion_detection_fer()
        fusion()

# Helper functions (use as before in your existing main.py)
def generate_questions(prompt, subdomain, domain_details, context=None, follow_up=False, question_type=None, asked_questions=None, topics=None, resume_data=None):
    """Generate interview questions with a mix of resume-based and subdomain-based prompts when relevant."""
    chat_session = model.start_chat(history=[])
    
    # Ensure asked_questions is a list
    if asked_questions is None:
        asked_questions = []
    
    # Check if resume data is relevant to the subdomain
    use_resume = resume_data and is_resume_relevant(resume_data, subdomain)
    
    # Prepare resume data prompt
    resume_prompt = ""
    if use_resume:
        # Since resume_data.py now guarantees strings, no need for to_string conversion
        projects = ", ".join(resume_data['projects']) if resume_data['projects'] else "None"
        experiences = ", ".join(resume_data['experiences']) if resume_data['experiences'] else "None"
        skills = ", ".join(resume_data['skills']) if resume_data['skills'] else "None"
        resume_prompt = (
            f"Candidate's resume details:\n"
            f"Projects (prioritize for questions): {projects}\n"
            f"Experiences (prioritize for questions): {experiences}\n"
            f"Skills: {skills}\n"
        )
    
    # Define weights: 70% resume-based, 30% subdomain-based when relevant
    if use_resume:
        question_source = random.choices(
            ['resume', 'subdomain'],
            weights=[0.7, 0.3],  # 70% resume, 30% subdomain
            k=1
        )[0]
    else:
        question_source = 'subdomain'
    
    # Construct prompt based on question source and context
    if follow_up and context:
        if question_source == 'resume':
            full_prompt = (
                f"{resume_prompt}\n"
                f"Based on the candidate's response '{context}', generate a detailed follow-up question in {subdomain}. "
                f"Focus on the candidate's projects and experiences from the resume, relating them to the response. "
                f"Ensure the question is phrased as a question and aligns with {subdomain}."
            )
        else:
            full_prompt = (
                f"{domain_details['llm_guidance']}\n"
                f"Based on the candidate's response '{context}', generate a detailed follow-up question in {subdomain}. "
                f"Focus on general concepts, challenges, or methodologies in {subdomain}. "
                f"Ensure the question is phrased as a question."
            )
    else:
        if question_source == 'resume':
            full_prompt = (
                f"{resume_prompt}\n"
                f"Generate a question in {subdomain} based primarily on the candidate's projects and experiences from the resume. "
                f"Ensure the question is specific to the resume details but aligns with {subdomain} topics. "
                f"Ensure the question is phrased as a question."
            )
        else:
            full_prompt = (
                f"{domain_details['llm_guidance']}\n{prompt}\n"
                f"Generate a question in {subdomain} based on general concepts, challenges, or methodologies. "
                f"Ensure the question is phrased as a question."
            )
        
        # Add question type and topics if applicable
        if question_type:
            full_prompt += f"\nQuestion type: {question_type}"
            if topics and question_type in topics:
                full_prompt += f"\nTopics: {topics[question_type]}"
    
    # Generate question with retry logic
    try:
        response = chat_session.send_message(full_prompt)
        if response.text:
            questions = [q.strip() for q in response.text.split('\n') if q.strip() and not q.startswith("#")]
            for question in questions:
                if question.endswith('?') and question not in asked_questions:
                    return question
            # Retry if no valid question
            retry_prompt = f"{full_prompt}\nEnsure the response is a direct question ending with a question mark."
            response = chat_session.send_message(retry_prompt)
            questions = [q.strip() for q in response.text.split('\n') if q.strip() and not q.startswith("#")]
            for question in questions:
                if question.endswith('?') and question not in asked_questions:
                    return question
        raise Exception("Failed to generate a question.")
    except Exception as e:
        print(f"Error generating question: {e}")
        raise

def should_follow_up(response):
    """Check if response is detailed enough for a follow-up."""
    keywords = ['experience', 'approach', 'method', 'challenge', 'solution', 'details', 'job', 'internship',
                'project', 'problem', 'implementation', 'design', 'optimization', 'tool', 'process', 'framework']
    return any(re.search(rf"\b{kw}\b", response, re.IGNORECASE) for kw in keywords)

def is_resume_relevant(resume_data, subdomain):
    """Check if resume data is relevant to the selected subdomain."""
    subdomain_keywords = {
        "Algorithms and Data Structures": [
            "algorithm", "data structure", "sorting", "searching", "graph", "tree",
            "array", "linked list", "hash table", "recursion", "complexity", "time complexity"
        ],
        "Artificial Intelligence and Machine Learning": [
            "machine learning", "deep learning", "neural network", "tensorflow", "pytorch",
            "data science", "algorithm", "model", "training", "prediction", "ai", "artificial intelligence"
        ],
        "Computer Networks": [
            "networking", "tcp/ip", "routing", "switching", "protocol", "lan", "wan",
            "firewall", "dns", "http", "subnet", "osi model"
        ],
        "Computer Vision": [
            "computer vision", "image processing", "opencv", "object detection", "face recognition",
            "image classification", "feature extraction", "segmentation", "cnn", "deep vision"
        ],
        "Cybersecurity": [
            "security", "encryption", "firewall", "penetration testing", "vulnerability",
            "authentication", "cryptography", "malware", "network security", "ethical hacking"
        ],
        "Data Science": [
            "data analysis", "statistics", "visualization", "pandas", "sql",
            "big data", "hadoop", "spark", "r", "tableau", "data mining"
        ],
        "Databases": [
            "database", "sql", "nosql", "mysql", "postgresql", "mongodb", "indexing",
            "query optimization", "normalization", "transaction", "schema"
        ],
        "Embedded Systems": [
            "embedded", "microcontroller", "raspberry pi", "arduino", "iot", "firmware",
            "real-time", "hardware", "c", "assembly", "sensor"
        ],
        "Game Development": [
            "game development", "unity", "unreal engine", "game design", "3d modeling",
            "animation", "physics engine", "opengl", "c#", "gamedev"
        ],
        "Operating Systems": [
            "operating system", "kernel", "process", "thread", "scheduler", "memory management",
            "file system", "virtualization", "linux", "windows", "unix"
        ],
        "Software Engineering": [
            "software development", "coding", "programming", "design pattern", "agile",
            "scrum", "java", "python", "javascript", "api", "devops"
        ],
        "Theoretical Computer Science": [
            "theory", "computability", "complexity", "turing machine", "automata",
            "formal language", "logic", "proof", "np-complete", "algorithm design"
        ]
    }
    
    keywords = subdomain_keywords.get(subdomain, [])
    if not keywords:
        return False
    
    # Convert all items to strings, handling dictionaries
    def to_string(item):
        if isinstance(item, dict):
            return " ".join(f"{k}: {v}" for k, v in item.items())
        return str(item)
    
    # Combine resume data into a single text for checking
    resume_text = " ".join(
        to_string(item)
        for category in [resume_data["projects"], resume_data["experiences"], resume_data["skills"]]
        for item in category
    ).lower()
    
    # Check for keyword matches
    return any(keyword.lower() in resume_text for keyword in keywords)