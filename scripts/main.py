import os
import time
import random
import json
import google.generativeai as genai
import re
import pyttsx3
from config_loader import load_domain_config, get_subdomains
from context_awareness import parse_transcription, extract_topics, sentiment_score
from recording_transcription import record_and_transcribe
from FER import emotion_detection_fer
from SER import emotion_detection_ser
from late_fusion import fusion
from report import generate_report
from txt_to_csv import convert_txt_to_csv
import scoring
from resume_data import extract_resume_info, save_resume_data

# Video and audio recording parameters
RATE = 44100
VIDEO_FPS = 20
VIDEO_SIZE = "640x480"

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

def format_topics(topics):
    """Extract words from topics string, e.g., "0.059*'model' + 0.044*'speech' + ..."""
    return ', '.join([word.split('*')[1].replace('"', '').strip() for word in topics.split('+')])

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

    resume_text = " ".join(
        str(item) for category in [resume_data["projects"], resume_data["experiences"], resume_data["skills"]]
        for item in category
    ).lower()
    return any(keyword.lower() in resume_text for keyword in keywords)

def enhanced_record_and_transcribe(video_filename, audio_filename, current_question):
    """Record video/audio, transcribe, and perform NLP tasks."""
    try:
        transcription = record_and_transcribe(video_filename, audio_filename)
        if transcription and not transcription.startswith("Transcription error"):
            parsed_data = parse_transcription(transcription)
            topics = extract_topics(transcription)
            sentiment = sentiment_score(transcription)
            formatted_topics = format_topics(topics[0] if topics else "")
            
            with open("session_history.txt", "a") as file:
                file.write(f"Question: \"{current_question}\"\n")
                file.write(f"Answer: \"{transcription}\"\n")
                file.write(f"Topics: {formatted_topics}\n")
                file.write(f"Sentiment: {sentiment}\n")
                file.write(f"Video: {video_filename}\n")
                file.write(f"Audio: {audio_filename}\n\n")
            
            return transcription, topics, sentiment, parsed_data
        return transcription, None, None, None
    except Exception as e:
        print(f"Error in recording/transcription: {e}")
        return "Transcription error", None, None, None
    finally:
        for file in [video_filename, audio_filename]:
            if os.path.exists(file):
                os.remove(file)

def should_follow_up(response):
    """Check if response is detailed enough for a follow-up."""
    keywords = ['experience', 'approach', 'method', 'challenge', 'solution', 'details', 'job', 'internship',
                'project', 'problem', 'implementation', 'design', 'optimization', 'tool', 'process', 'framework']
    return any(re.search(rf"\b{kw}\b", response, re.IGNORECASE) for kw in keywords)

def generate_questions(prompt, subdomain, domain_details, context=None, follow_up=False, question_type=None, asked_questions=None, topics=None, resume_data=None):
    """Generate interview questions with a mix of resume-based and subdomain-based prompts, prioritizing real-world relevance."""
    chat_session = model.start_chat(history=[])
    if asked_questions is None:
        asked_questions = []

    # Check resume relevance
    use_resume = resume_data and is_resume_relevant(resume_data, subdomain)

    # Resume prompt for relevant subdomains
    resume_prompt = ""
    if use_resume:
        projects = ", ".join(resume_data['projects']) if resume_data['projects'] else "None"
        experiences = ", ".join(resume_data['experiences']) if resume_data['experiences'] else "None"
        skills = ", ".join(resume_data['skills']) if resume_data['skills'] else "None"
        resume_prompt = (
            f"Candidate's resume details:\n"
            f"Projects (highest priority): {projects}\n"
            f"Experiences (high priority): {experiences}\n"
            f"Skills (supporting context): {skills}\n"
        )

    # Select question source: 70% resume-based, 30% subdomain-based if relevant
    question_source = 'subdomain'
    if use_resume:
        question_source = random.choices(
            ['resume', 'subdomain'],
            weights=[0.7, 0.3],
            k=1
        )[0]

    # Real-world question templates
    question_templates = {
        'technical': [
            "Explain how you implemented {project_detail} in {project}. What technical challenges did you face?",
            "How did you use {skill} in {project} to achieve {outcome}?",
            "Describe the architecture of {project}. Why did you choose {technology}?"
        ],
        'behavioral': [
            "Tell me about a challenge you faced in {project/experience} and how you resolved it.",
            "Describe a time in {experience} when you demonstrated {skill}. What was the impact?",
            "How did you handle a conflict or setback in {project}?"
        ],
        'situational': [
            "Given your experience with {skill}, how would you approach {subdomain_problem} in a new project?",
            "If tasked with optimizing {project_component}, what steps would you take based on your {experience}?",
            "How would you apply {skill} to solve {subdomain_challenge}?"
        ]
    }

    # Construct prompt
    if follow_up and context:
        if question_source == 'resume':
            full_prompt = (
                f"{resume_prompt}\n"
                f"Based on the candidate's response '{context}', generate a follow-up question in {subdomain}. "
                f"Choose a {question_type} question style from: {', '.join(question_templates.keys())}. "
                f"Focus on the candidate's projects and experiences, relating them to the response. "
                f"Use real-world interview question patterns (technical, behavioral, or situational). "
                f"Ensure the question is concise, specific, and ends with a question mark."
            )
        else:
            full_prompt = (
                f"{domain_details['llm_guidance']}\n"
                f"Based on the candidate's response '{context}', generate a follow-up question in {subdomain}. "
                f"Choose a {question_type} question style from: {', '.join(question_templates.keys())}. "
                f"Focus on general concepts, challenges, or methodologies in {subdomain}. "
                f"Use real-world interview question patterns (technical, behavioral, or situational). "
                f"Ensure the question is concise, specific, and ends with a question mark."
            )
    else:
        if question_source == 'resume':
            full_prompt = (
                f"{resume_prompt}\n"
                f"Generate a {question_type} question in {subdomain} based primarily on the candidate's projects and experiences. "
                f"Choose a question style from: {', '.join(question_templates.keys())}. "
                f"Ensure the question is specific to resume details, aligns with {subdomain}, and mimics real-world interview questions. "
                f"Ensure the question is concise, specific, and ends with a question mark."
            )
        else:
            full_prompt = (
                f"{domain_details['llm_guidance']}\n{prompt}\n"
                f"Generate a {question_type} question in {subdomain} based on general concepts, challenges, or methodologies. "
                f"Choose a question style from: {', '.join(question_templates.keys())}. "
                f"Ensure the question aligns with {subdomain} and mimics real-world interview questions. "
                f"Ensure the question is concise, specific, and ends with a question mark."
            )

    # Add topics if applicable
    if question_type and topics and question_type in topics:
        full_prompt += f"\nRelevant topics: {topics[question_type]}"

    # Generate question with retry logic
    try:
        response = chat_session.send_message(full_prompt)
        if response.text:
            questions = [q.strip() for q in response.text.split('\n') if q.strip() and q.endswith('?')]
            for question in questions:
                if question not in asked_questions:
                    return question
        # Retry with stricter instructions
        retry_prompt = f"{full_prompt}\nEnsure the response is a single, concise question ending with a question mark."
        response = chat_session.send_message(retry_prompt)
        questions = [q.strip() for q in response.text.split('\n') if q.strip() and q.endswith('?')]
        for question in questions:
            if question not in asked_questions:
                return question
        raise Exception("Failed to generate a valid question.")
    except Exception as e:
        print(f"Error generating question: {e}")
        raise


def conduct_interview():
    """Conduct the interview with resume integration and adaptive questions."""
    resume_path = r"C:\Users\uarif\Desktop\Cv's\V6\UsmanArif_resume.pdf"
    if not os.path.exists(resume_path) or not resume_path.lower().endswith('.pdf'):
        print(f"Error: Resume file {resume_path} does not exist or is not a PDF.")
        return
    
    resume_data = extract_resume_info(resume_path)
    save_resume_data(resume_data)
    
    session_history_path = "session_history.txt"
    with open(session_history_path, "w") as file:
        file.write("")
    
    subdomains = get_subdomains()
    print("Please select the subdomain you want to be interviewed in:")
    for idx, domain in enumerate(subdomains, 1):
        print(f"{idx}. {domain}")
    selected_idx = int(input("Enter the number of the subdomain: ")) - 1
    selected_subdomain = subdomains[selected_idx]
    
    subdomain_file = f"{selected_subdomain.replace(' ', '_').lower()}.txt"
    domain_details, intro_prompt, question_distribution, topics = load_domain_config(subdomain_file)
    
    prompt = f"You are conducting an interview for a role in {selected_subdomain}."
    context_history = []
    asked_questions = []
    
    total_questions = int(input("Enter number of questions: "))
    question_counts = {key: round(total_questions * (value / 100)) for key, value in question_distribution.items()}
    
    while sum(question_counts.values()) < total_questions:
        for key in question_counts:
            if question_counts[key] < total_questions * (question_distribution[key] / 100):
                question_counts[key] += 1
                break
    
    for i in range(total_questions):
        if i == 0:
            question = generate_questions(intro_prompt, selected_subdomain, domain_details, topics=topics, resume_data=resume_data, asked_questions=asked_questions)
            print(f"Q1: {question}")
            speak(question)
        else:
            question_type = random.choices(list(question_counts.keys()), weights=list(question_counts.values()))[0]
            question_counts[question_type] -= 1
            context = context_history[-1] if context_history else None
            question = generate_questions(
                prompt, selected_subdomain, domain_details, context=context,
                follow_up=bool(context and should_follow_up(context)),
                question_type=question_type, asked_questions=asked_questions,
                topics=topics, resume_data=resume_data
            )
            print(f"\n--- {question_type.upper()} QUESTION ---")
            print(f"Q{i+1}: {question}")
            speak(question)
        
        print("You have 10 seconds to understand the question...")
        time.sleep(1)
        
        video_file = os.path.abspath(f"response_{selected_subdomain}_{i+1}_with_audio.mp4")
        audio_file = os.path.abspath(f"response_{selected_subdomain}_{i+1}.wav")
        transcription, topics, sentiment, parsed_data = enhanced_record_and_transcribe(video_file, audio_file, question)
        
        question_sentiments = {}
        if transcription and not transcription.startswith("Transcription error"):
            context_history.append(transcription)
            question_number = i + 1
            question_sentiments[f"Q{question_number}"] = sentiment
        else:
            context_history.append("No answer provided due to transcription error.")
            question_number = i + 1
            question_sentiments[f"Q{question_number}"] = "N/A"
        
        asked_questions.append(question)
    
    convert_txt_to_csv(session_history_path, "session_history.csv")
    scoring.evaluate_answers_and_save()
    emotion_detection_ser()
    emotion_detection_fer()
    fusion()
    generate_report("evaluation_results.json", "fused_emotion_predictions.json")

if __name__ == "__main__":
    conduct_interview()