# 🤖 ASAAN INTERVIEW – AI Multimodal Interview Assistant Bot

## 📝 Overview

**ASAAN INTERVIEW** is an AI-powered multimodal interview assistant bot developed as our Final Year Project. It simulates an intelligent interviewer that can ask personalized technical questions, analyze behavioral patterns, and provide a detailed evaluation report — all in a secure and remote environment.

This system leverages LLMs, audio/video analysis, facial & vocal emotion recognition, resume-based personalization, and cheating surveillance to make virtual interviews smarter, fairer, and more insightful.

## ✨ Key Features

- ⚙️ Domain-specific question generation using Large Language Models (LLMs)
- 📄 Resume extraction to personalize questions based on experience and projects
- 🎙️ Speech Emotion Recognition (SER)
- 🎥 Facial Emotion Recognition (FER)
- ❤️ Sentiment Analysis with late fusion of SER & FER
- 🔍 Cheating Surveillance Module: head pose, gaze direction, mobile detection
- 📊 Auto-generated detailed performance report (PDF)

## 🧩 Core Modules

### 1️⃣ LLM-Based Question Generation
- Generates technical questions tailored to selected domain (e.g., Computer vision, AI, SE)
- Integrates context from resume to make questions highly relevant

### 2️⃣ Resume-Based Personalization
- Extracts details like:
  - Work experience
  - Projects
  - Technical skills
- Used to align question generation with real background

### 3️⃣ Emotion & Sentiment Analysis
- **Speech Emotion Recognition (SER)**: Detects tone & vocal emotions
- **Facial Emotion Recognition (FER)**: Real-time facial expression detection
- **Late Fusion**: Combines SER & FER to enhance emotion classification accuracy
- **Sentiment Analysis**: Evaluates polarity of verbal answers

### 4️⃣ Cheating Surveillance System
- Ensures fairness in remote settings using computer vision:
  - 👀 Eye movement & gaze detection (via Dlib)
  - 🧠 Head pose estimation (solvePnP algorithm)
  - 📱 Real-time mobile phone detection using YOLOv12
- Flags behavioral anomalies like repeated distractions, looking away, or device usage

### 5️⃣ Report Generation
- Summarizes candidate performance into a visual PDF report
- Includes:
  - Domain-wise Q/A scores
  - Emotion/sentiment timelines
  - Gaze/head behavior analysis
  - Cheating alerts

## 💼 Use Cases

- 🧑‍💻 **Remote Job Interviews** – Conduct AI-based interviews and performance analysis
- 🎓 **Online Exams & Viva** – Ensure academic integrity and evaluate expressiveness
- 🤖 **AI Interview Practice** – Students & professionals can practice and receive feedback
- 📈 **HR and Candidate Profiling** – Fair evaluation with emotional intelligence metrics

## Contributions  
Contributions are welcome! Feel free to fork the repo, make improvements, and submit a pull request.  

## License  
This project is licensed under the MIT License.  

🚀 **Get started with AI-driven interviews today!**
