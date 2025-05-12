import json
import pdfplumber
import time
import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Gemini model config
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "max_output_tokens": 2000,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)

def extract_resume_info(file_path):
    """Extract projects, experiences, and skills from a PDF resume using Gemini LLM."""
    try:
        # Step 1: Extract raw text from PDF
        with pdfplumber.open(file_path) as pdf:
            text = "".join(page.extract_text() or "" for page in pdf.pages)

        #print("📝 Extracted Text:\n", text[:1000])  # Limit output for large resumes

        if not text.strip():
            print("❌ Error: No text extracted from resume.")
            return {"projects": [], "experiences": [], "skills": []}

        # Step 2: Build prompt
        prompt = (
            "You are an expert resume parser. Given the following resume text, extract the following information:\n"
            "- Projects: List any projects mentioned, each as a single string combining name and description (e.g., 'Chatbot Development: Built using TensorFlow').\n"
            "- Experiences: List work experiences, each as a single string combining company, role, dates, and description (e.g., 'Google, Software Engineer, 2020-2022: Developed AI models').\n"
            "- Skills: List technical skills, each as a single string (e.g., 'Python', 'SQL').\n"
            "Return the output in JSON format with keys 'projects', 'experiences', and 'skills', each containing a list of strings.\n"
            "Do not return dictionaries within the lists; combine all details into a single string for each item.\n"
            "Ignore personal info and education unless relevant to skills.\n"
            "Resume text:\n"
            f"{text}\n"
            "Output format:\n"
            "```json\n"
            "{\n"
            "  \"projects\": [\"Chatbot Development: Built using TensorFlow\", \"Image Classifier: Used PyTorch\"],\n"
            "  \"experiences\": [\"Google, Software Engineer, 2020-2022: Developed AI models\", \"Amazon, Data Scientist, 2022-Present: Analyzed big data\"],\n"
            "  \"skills\": [\"Python\", \"SQL\", \"TensorFlow\", \"AWS\"]\n"
            "}\n"
            "```"
        )

        # Step 3: Call Gemini
        chat = model.start_chat(history=[])
        for attempt in range(3):
            try:
                response = chat.send_message(prompt)
                break
            except Exception as e:
                print(f"⚠️ API error on attempt {attempt + 1}: {e}")
                time.sleep(2)
        else:
            return {"projects": [], "experiences": [], "skills": []}

        if not response.text:
            print("❌ Error: Gemini returned empty response.")
            return {"projects": [], "experiences": [], "skills": []}

        #print("📨 Gemini Raw Response:\n", response.text)

        # Step 4: Extract JSON content from markdown
        json_text = response.text.strip()
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0].strip()

        print("🧼 Cleaned JSON Text:\n", json_text)

        # Step 5: Parse JSON safely
        try:
            data = json.loads(json_text)
            # Convert all items to strings, handling any unexpected dictionaries
            def to_string(item):
                if isinstance(item, dict):
                    # Combine dict into a single string (e.g., {'company': 'Google', 'role': 'Engineer'} -> 'Google, Engineer')
                    parts = [f"{v}" for k, v in item.items() if v]
                    return ", ".join(parts)
                return str(item)

            projects = [to_string(item) for item in data.get("projects", [])]
            experiences = [to_string(item) for item in data.get("experiences", [])]
            skills = [to_string(item) for item in data.get("skills", [])]

            result = {
                "projects": projects,
                "experiences": experiences,
                "skills": skills
            }
            print("✅ Extracted Projects:", result["projects"])
            print("✅ Extracted Experiences:", result["experiences"])
            print("✅ Extracted Skills:", result["skills"])
            return result
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            return {"projects": [], "experiences": [], "skills": []}

    except Exception as e:
        print(f"❌ Error processing resume: {e}")
        return {"projects": [], "experiences": [], "skills": []}

def save_resume_data(resume_data, output_file="resume_data.json"):
    """Save resume data to JSON file."""
    try:
        with open(output_file, "w") as f:
            json.dump(resume_data, f, indent=2)
        print(f"📁 Resume data saved to {output_file}")
    except Exception as e:
        print(f"❌ Error saving resume data: {e}")

if __name__ == "__main__":
    resume_path = r"C:\Users\uarif\Desktop\owais_resume-1.pdf"  # Change this path
    output_file = "resume_data_1.json"

    resume_data = extract_resume_info(resume_path)
    save_resume_data(resume_data, output_file)