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
    # We'll split on '+' and extract only the word part
    return ', '.join([word.split('*')[1].replace('"', '').strip() for word in topics.split('+')])

def enhanced_record_and_transcribe(filename, current_question):
    transcription = record_and_transcribe(filename)  # Use existing function to record and transcribe

    if transcription:
        # Perform NLP tasks
        parsed_data = parse_transcription(transcription)
        topics = extract_topics(transcription)
        sentiment = sentiment_score(transcription)

        # Format topics for better readability
        formatted_topics = format_topics(topics[0] if topics else "")

        # Save session data
        with open("session_history.txt", "a") as file:
            file.write(f"Question: \"{current_question}\"\n")
            file.write(f"Answer: \"{transcription}\"\n")
            file.write(f"Topics: {formatted_topics}\n")
            file.write(f"Sentiment: {sentiment}\n\n")

        return transcription, topics, sentiment

    return transcription, None, None

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
    """Conducts an AI interview while recording video and keeping all functionalities intact."""
    
    # File path for session history
    session_history_path = "session_history.txt"
    with open(session_history_path, "w") as file:
        file.write("")  # Clear previous session history

    # Load subdomains and let the user choose one
    subdomains = get_subdomains()
    print("Please select the subdomain you want to be interviewed in:")
    for idx, domain in enumerate(subdomains, 1):
        print(f"{idx}. {domain}")
    
    selected_idx = int(input("Enter the number of the subdomain: ")) - 1
    selected_subdomain = subdomains[selected_idx]

    # Start video recording (FULL SESSION)
    video_thread = start_video_recording()

    try:
        # Load domain-specific configurations
        subdomain_file = f"{selected_subdomain.replace(' ', '_').lower()}.txt"
        domain_details, intro_prompt, question_distribution, topics = load_domain_config(subdomain_file)

        # Initialize interview parameters
        prompt = f"You are conducting an interview for a role in {selected_subdomain}."
        context = None
        asked_questions = []
        total_questions = 2  # Example total questions

        # Ensure proper question distribution
        question_counts = {key: round(total_questions * (value / 100)) for key, value in question_distribution.items()}
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
                # First predefined question
                print(f"Q1: {question}")
                speak(question)
            else:
                # Generate follow-up or new question
                question_type = random.choices(list(question_counts.keys()), weights=list(question_counts.values()))[0]
                question_counts[question_type] -= 1

                if context and should_follow_up(context):
                    question = generate_questions(prompt, selected_subdomain, domain_details, context=context, follow_up=True, asked_questions=asked_questions, topics=topics)
                else:
                    question = generate_questions(prompt, selected_subdomain, domain_details, question_type=question_type, asked_questions=asked_questions, topics=topics)

                print(f"\n--- {question_type.upper()} QUESTION ---")
                print(f"Q{i+1}: {question}")
                speak(question)

            # Small delay to allow the user to process the question
            print("You have 10 seconds to understand the question...")
            time.sleep(1)

            # Record and transcribe response
            audio_file = os.path.abspath(f"response_{selected_subdomain}_{i+1}.wav")
            transcription, topics, sentiment = enhanced_record_and_transcribe(audio_file, question)

            if transcription and not transcription.startswith("Transcription error"):
                print(f"Answer {i+1}: {transcription}")
                context = transcription
            else:
                context = "No answer provided due to transcription error."

            asked_questions.append(question)

        # Post-interview processing
        convert_txt_to_csv(session_history_path, "session_history.csv")
        scoring.evaluate_answers_and_save()
        SER.sentiment()
        gen_report.generate_report("evaluation_results.json", "emotion_predictions_multiple.json")

        print("Interview complete!")

    finally:
        # Stop video recording once interview ends
        stop_video_recording(video_thread)

#version without audio vidoe recording and transcription error if speech is intangible not giving the option to answer again
# def conduct_interview():
#     """Conducts an AI interview while recording video and keeping all functionalities intact."""
    
#     # File path for session history
#     session_history_path = "session_history.txt"
#     with open(session_history_path, "w") as file:
#         file.write("")  # Clear previous session history

#     # Load subdomains and let the user choose one
#     subdomains = get_subdomains()
#     print("Please select the subdomain you want to be interviewed in:")
#     for idx, domain in enumerate(subdomains, 1):
#         print(f"{idx}. {domain}")
    
#     selected_idx = int(input("Enter the number of the subdomain: ")) - 1
#     selected_subdomain = subdomains[selected_idx]

#     # Start video recording (FULL SESSION)
#     video_thread = start_video_recording()

#     try:
#         # Load domain-specific configurations
#         subdomain_file = f"{selected_subdomain.replace(' ', '_').lower()}.txt"
#         domain_details, intro_prompt, question_distribution, topics = load_domain_config(subdomain_file)

#         # Initialize interview parameters
#         prompt = f"You are conducting an interview for a role in {selected_subdomain}."
#         context = None
#         asked_questions = []
#         total_questions = 2  # Example total questions

#         # Ensure proper question distribution
#         question_counts = {key: round(total_questions * (value / 100)) for key, value in question_distribution.items()}
#         while sum(question_counts.values()) < total_questions:
#             for key in question_counts:
#                 if question_counts[key] < total_questions * (question_distribution[key] / 100):
#                     question_counts[key] += 1
#                     break

#         # Start the interview with the first question
#         first_question = generate_questions(intro_prompt, selected_subdomain, domain_details, topics=topics)
#         question = first_question

#         for i in range(total_questions):
#             if i == 0:
#                 # First predefined question
#                 print(f"Q1: {question}")
#                 speak(question)
#             else:
#                 # Generate follow-up or new question
#                 question_type = random.choices(list(question_counts.keys()), weights=list(question_counts.values()))[0]
#                 question_counts[question_type] -= 1

#                 if context and should_follow_up(context):
#                     question = generate_questions(prompt, selected_subdomain, domain_details, context=context, follow_up=True, asked_questions=asked_questions, topics=topics)
#                 else:
#                     question = generate_questions(prompt, selected_subdomain, domain_details, question_type=question_type, asked_questions=asked_questions, topics=topics)

#                 print(f"\n--- {question_type.upper()} QUESTION ---")
#                 print(f"Q{i+1}: {question}")
#                 speak(question)

#             # Small delay to allow the user to process the question
#             print("You have 10 seconds to understand the question...")
#             time.sleep(1)

#             # Record and transcribe response
#             audio_file = os.path.abspath(f"response_{selected_subdomain}_{i+1}.wav")
#             transcription, topics, sentiment = enhanced_record_and_transcribe(audio_file, question)

#             if transcription and not transcription.startswith("Transcription error"):
#                 print(f"Answer {i+1}: {transcription}")
#                 context = transcription
#             else:
#                 context = "No answer provided due to transcription error."

#             # Log session history
#             with open(session_history_path, "a") as file:
#                 file.write(f"Question: \"{question}\"\n")
#                 file.write(f"Answer: \"{transcription if transcription else 'No response'}\"\n")
#                 file.write(f"Topics: {', '.join(topics) if topics else 'N/A'}\n")
#                 file.write(f"Sentiment: {sentiment if sentiment else 'N/A'}\n\n")

#             asked_questions.append(question)

#         # Post-interview processing
#         convert_txt_to_csv(session_history_path, "session_history.csv")
#         scoring.evaluate_answers_and_save()
#         SER.sentiment()
#         gen_report.generate_report("evaluation_results.json", "emotion_predictions_multiple.json")

#         print("Interview complete!")

#     finally:
#         # Stop video recording once interview ends
#         stop_video_recording(video_thread)

#version original
# def conduct_interview():
#     # File path for the session history
#     session_history_path = "session_history.txt"

#     # Open the file in write mode ('w') to overwrite old content or create a new one if it doesn't exist
#     with open(session_history_path, "w") as file:
#         file.write("")

#     # Load subdomains
#     subdomains = get_subdomains()
    
#     # Select subdomain
#     print("Please select the subdomain you want to be interviewed in:")
#     for idx, domain in enumerate(subdomains, 1):
#         print(f"{idx}. {domain}")
    
#     selected_idx = int(input("Enter the number of the subdomain: ")) - 1
#     selected_subdomain = subdomains[selected_idx]

#     # Load domain details, intro prompt, first question, question distribution, and topics
#     subdomain_file = f"{selected_subdomain.replace(' ', '_').lower()}.txt"
#     domain_details, intro_prompt, question_distribution, topics = load_domain_config(subdomain_file)

#     # Initialize prompt and context
#     prompt = f"You are conducting an interview for a role in {selected_subdomain}."
#     context = None
#     asked_questions = []

#     # Calculate the number of questions for each type
#     total_questions = 2  # Example total number of questions
#     question_counts = {key: round(total_questions * (value / 100)) for key, value in question_distribution.items()}

#     # Ensure the total number of questions is correct
    
#     while sum(question_counts.values()) < total_questions:
#         for key in question_counts:
#             if question_counts[key] < total_questions * (question_distribution[key] / 100):
#                 question_counts[key] += 1
#                 break

#     # Start the interview with the first question
#     first_question = generate_questions(intro_prompt, selected_subdomain, domain_details, topics=topics)
#     question = first_question

#     for i in range(total_questions):
#         if i == 0:
#             # Use the predefined first question for the first round
#             print(f"Q1: {question}")
#             speak(question)
#         else:
#             # Determine the type of question to generate
#             question_type = random.choices(list(question_counts.keys()), weights=list(question_counts.values()))[0]
#             question_counts[question_type] -= 1

#             # Generate a follow-up or new question based on context
#             if context and should_follow_up(context):
#                 question = generate_questions(prompt, selected_subdomain, domain_details, context=context, follow_up=True, asked_questions=asked_questions, topics=topics)
#             else:
#                 question = generate_questions(prompt, selected_subdomain, domain_details, question_type=question_type, asked_questions=asked_questions, topics=topics)

#             # Print the question type heading before the question
#             print(f"\n--- {question_type.upper()} QUESTION ---")
#             print(f"Q{i+1}: {question}")
#             speak(question)

#         # Wait for a short time for user to read the question
#         print("You have 10 seconds to understand the question...")
#         time.sleep(1)

#         audio_file = os.path.abspath(f"response_{selected_subdomain}_{i+1}.wav")
#         transcription, topics, sentiment = enhanced_record_and_transcribe(audio_file, question)

#         if transcription and not transcription.startswith("Transcription error"):
#             print(f"Answer {i+1}: {transcription}")
#             context = transcription
#         else:
#             context = "No answer provided due to transcription error."

#         # Add the asked question to the list
#         asked_questions.append(question)
#     convert_txt_to_csv(session_history_path, "session_history.csv")
#     scoring.evaluate_answers_and_save()
#     SER.sentiment()
#     gen_report.generate_report("evaluation_results.json", "emotion_predictions_multiple.json")
    

if __name__ == "__main__":
    conduct_interview()
