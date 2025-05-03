import json
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
import os
import numpy as np

def generate_report(eval_results_file, emotion_results_file, fer_results_file=None):
    """
    Generate a comprehensive report incorporating evaluation results, 
    speech emotion recognition, and facial emotion recognition data.
    """
    # Create report directory if it doesn't exist
    if not os.path.exists('reports'):
        os.makedirs('reports')
    
    # Load evaluation results
    with open(eval_results_file, 'r') as f:
        eval_data = json.load(f)
    
    # Load SER emotion results
    with open(emotion_results_file, 'r') as f:
        emotion_data = json.load(f)
    
    # Load FER results if available
    fer_data = None
    if fer_results_file and os.path.exists(fer_results_file):
        with open(fer_results_file, 'r') as f:
            fer_data = json.load(f)
    
    # Calculate average scores
    technical_scores = [q['technical_score'] for q in eval_data.values()]
    communication_scores = [q['communication_score'] for q in eval_data.values()]
    relevance_scores = [q['relevance_score'] for q in eval_data.values()]
    
    avg_technical = sum(technical_scores) / len(technical_scores) if technical_scores else 0
    avg_communication = sum(communication_scores) / len(communication_scores) if communication_scores else 0
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
    overall_score = (avg_technical + avg_communication + avg_relevance) / 3
    
    # Create timestamp for report filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"reports/interview_report_{timestamp}.html"
    
    # Generate emotion visualization
    emotion_chart_path = f"reports/emotion_chart_{timestamp}.png"
    generate_emotion_chart(emotion_data, fer_data, emotion_chart_path)
    
    # Generate score visualization
    score_chart_path = f"reports/score_chart_{timestamp}.png"
    generate_score_chart(eval_data, score_chart_path)
    
    # Create HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Interview Analysis Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                color: #333;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                background: #fff;
                padding: 20px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            h1, h2, h3 {{
                color: #2c3e50;
            }}
            .summary {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .score {{
                font-size: 24px;
                font-weight: bold;
                color: #2980b9;
            }}
            .question-section {{
                margin-bottom: 30px;
                border-bottom: 1px solid #eee;
                padding-bottom: 20px;
            }}
            .chart-container {{
                margin: 20px 0;
                text-align: center;
            }}
            .score-breakdown {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 15px;
            }}
            .score-item {{
                flex: 1;
                text-align: center;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
                margin: 0 5px;
            }}
            .emotions-section {{
                margin-top: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                padding: 12px 15px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }}
            th {{
                background-color: #f8f9fa;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Interview Analysis Report</h1>
            <p>Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <div class="summary">
                <h2>Overall Assessment</h2>
                <p>Overall Score: <span class="score">{overall_score:.2f}/10.0</span></p>
                <div class="score-breakdown">
                    <div class="score-item">
                        <h3>Technical Knowledge</h3>
                        <div class="score">{avg_technical:.2f}/10.0</div>
                    </div>
                    <div class="score-item">
                        <h3>Communication</h3>
                        <div class="score">{avg_communication:.2f}/10.0</div>
                    </div>
                    <div class="score-item">
                        <h3>Relevance</h3>
                        <div class="score">{avg_relevance:.2f}/10.0</div>
                    </div>
                </div>
            </div>
            
            <div class="chart-container">
                <h2>Score Distribution</h2>
                <img src="{score_chart_path}" alt="Score Distribution" style="max-width:100%;">
            </div>
            
            <div class="emotions-section">
                <h2>Emotional Analysis</h2>
                <p>This section analyzes the candidate's emotional state during the interview, based on both voice and facial expressions.</p>
                
                <div class="chart-container">
                    <img src="{emotion_chart_path}" alt="Emotion Analysis" style="max-width:100%;">
                </div>
                
                <h3>Question-by-Question Analysis</h3>
                <table>
                    <tr>
                        <th>Question</th>
                        <th>Voice Emotion</th>
                        <th>Facial Emotion</th>
                        <th>Technical Score</th>
                        <th>Communication Score</th>
                        <th>Relevance Score</th>
                    </tr>
    """
    
    # Add question-by-question analysis
    for q_num, q_data in eval_data.items():
        question_id = q_num
        
        # Get voice emotion if available
        voice_emotion = "N/A"
        if question_id in emotion_data:
            voice_emotion = emotion_data[question_id]["predicted_emotion"]
        
        # Get facial emotion if available
        facial_emotion = "N/A"
        if fer_data and question_id in fer_data:
            facial_emotion = fer_data[question_id]["dominant_emotion"]
        
        html_content += f"""
                    <tr>
                        <td>Q{question_id}</td>
                        <td>{voice_emotion}</td>
                        <td>{facial_emotion}</td>
                        <td>{q_data['technical_score']}/10</td>
                        <td>{q_data['communication_score']}/10</td>
                        <td>{q_data['relevance_score']}/10</td>
                    </tr>
        """
    
    html_content += """
                </table>
            </div>
            
            <h2>Detailed Question Analysis</h2>
    """
    
    # Add detailed analysis for each question
    for q_num, q_data in eval_data.items():
        question_id = q_num
        
        html_content += f"""
            <div class="question-section">
                <h3>Question {question_id}</h3>
                <p><strong>Question:</strong> {q_data['question']}</p>
                <p><strong>Answer:</strong> {q_data['answer']}</p>
                
                <div class="score-breakdown">
                    <div class="score-item">
                        <h4>Technical: {q_data['technical_score']}/10</h4>
                    </div>
                    <div class="score-item">
                        <h4>Communication: {q_data['communication_score']}/10</h4>
                    </div>
                    <div class="score-item">
                        <h4>Relevance: {q_data['relevance_score']}/10</h4>
                    </div>
                </div>
                
                <p><strong>Feedback:</strong> {q_data['feedback']}</p>
                
                <h4>Emotional Analysis:</h4>
        """
        
        # Add voice emotion data
        if question_id in emotion_data:
            html_content += f"""
                <p><strong>Voice Emotion:</strong> {emotion_data[question_id]["predicted_emotion"]}</p>
            """
        
        # Add facial emotion data
        if fer_data and question_id in fer_data:
            html_content += f"""
                <p><strong>Facial Emotion:</strong> {fer_data[question_id]["dominant_emotion"]}</p>
                <p><strong>Facial Emotion Breakdown:</strong></p>
                <ul>
            """
            
            for emotion, percentage in fer_data[question_id]["emotion_percentages"].items():
                html_content += f"""
                    <li>{emotion.capitalize()}: {percentage:.2f}%</li>
                """
                
            html_content += """
                </ul>
            """
            
        html_content += """
            </div>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    # Write HTML report to file
    with open(report_filename, 'w') as f:
        f.write(html_content)
    
    print(f"Report generated successfully: {report_filename}")
    return report_filename

def generate_emotion_chart(emotion_data, fer_data, output_path):
    """Generate a chart comparing speech and facial emotions."""
    plt.figure(figsize=(12, 8))
    
    # Set up question numbers
    question_ids = sorted(list(emotion_data.keys()))
    x = np.arange(len(question_ids))
    
    # Set width of bars
    width = 0.35
    
    # Extract voice emotions
    voice_emotions = [emotion_data[q_id]["predicted_emotion"] for q_id in question_ids]
    unique_voice_emotions = list(set(voice_emotions))
    voice_emotion_counts = {emotion: [1 if voice_emotions[i] == emotion else 0 for i in range(len(question_ids))] 
                            for emotion in unique_voice_emotions}
    
    # Create subplot for voice emotions
    plt.subplot(2, 1, 1)
    bottom = np.zeros(len(question_ids))
    
    for emotion, counts in voice_emotion_counts.items():
        plt.bar(x, counts, width, label=emotion, bottom=bottom)
        bottom += counts
    
    plt.title('Voice Emotion Analysis by Question')
    plt.xlabel('Question Number')
    plt.ylabel('Emotion')
    plt.xticks(x, [f'Q{q_id}' for q_id in question_ids])
    plt.legend()
    
    # Create subplot for facial emotions if available
    if fer_data:
        plt.subplot(2, 1, 2)
        
        # Prepare data
        emotions_to_plot = ['happy', 'neutral', 'sad', 'surprise', 'anger', 'disgust', 'fear']
        emotion_data_by_question = []
        
        for q_id in question_ids:
            if q_id in fer_data:
                emotion_percentages = [fer_data[q_id]["emotion_percentages"].get(emotion, 0) for emotion in emotions_to_plot]
            else:
                emotion_percentages = [0] * len(emotions_to_plot)
            emotion_data_by_question.append(emotion_percentages)
        
        # Plot stacked bar chart
        bottom = np.zeros(len(question_ids))
        for i, emotion in enumerate(emotions_to_plot):
            values = [data[i] for data in emotion_data_by_question]
            plt.bar(x, values, width, label=emotion, bottom=bottom)
            bottom += values
        
        plt.title('Facial Emotion Analysis by Question')
        plt.xlabel('Question Number')
        plt.ylabel('Emotion Percentage')
        plt.xticks(x, [f'Q{q_id}' for q_id in question_ids])
        plt.legend()
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def generate_score_chart(eval_data, output_path):
    """Generate a chart visualizing interview scores."""
    question_ids = sorted(list(eval_data.keys()))
    
    # Extract scores
    technical_scores = [eval_data[q_id]['technical_score'] for q_id in question_ids]
    communication_scores = [eval_data[q_id]['communication_score'] for q_id in question_ids]
    relevance_scores = [eval_data[q_id]['relevance_score'] for q_id in question_ids]
    
    x = np.arange(len(question_ids))
    width = 0.25
    
    plt.figure(figsize=(12, 6))
    plt.bar(x - width, technical_scores, width, label='Technical')
    plt.bar(x, communication_scores, width, label='Communication')
    plt.bar(x + width, relevance_scores, width, label='Relevance')
    
    plt.title('Interview Scores by Question')
    plt.xlabel('Question Number')
    plt.ylabel('Score (out of 10)')
    plt.xticks(x, [f'Q{q_id}' for q_id in question_ids])
    plt.legend()
    plt.ylim(0, 10)
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

if __name__ == "__main__":
    generate_report("evaluation_results.json", "emotion_predictions_multiple.json", "fer_results.json")