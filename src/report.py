import json
import os

def extract_scores(feedback):
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

        accuracy, clarity, preciseness = extract_scores(feedback)
        new_data["stackedBarChartData"]["labels"].append(f"Q{i+1}")
        new_data["stackedBarChartData"]["datasets"][0]["data"].append(accuracy)
        new_data["stackedBarChartData"]["datasets"][1]["data"].append(preciseness)
        new_data["stackedBarChartData"]["datasets"][2]["data"].append(clarity)

    return new_data

def parse_fused_emotion_json(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    bar_chart_data = {
        "labels": [],
        "scores": [],
        "colors": [],
        "question_mapping": {}
    }
    emotion_colors = {
        "neutral": "rgba(150, 150, 150, 0.65)",
        "angry": "rgba(220, 0, 0, 0.65)",
        "sad": "rgba(0, 0, 200, 0.65)",
        "fear": "rgba(220, 140, 0, 0.65)",
        "surprise": "rgba(255, 220, 0, 0.65)",
        "disgust": "rgba(180, 0, 180, 0.65)"
    }

    for i, item in enumerate(data):
        # Get the segment with the highest confidence for this file
        if item["segments"]:
            max_segment = max(item["segments"], key=lambda x: x.get("confidence", 0))
            dominant_emotion = max_segment["dominant_emotion"]
            confidence = max_segment["confidence"]
            bar_chart_data["labels"].append(dominant_emotion)
            bar_chart_data["scores"].append(confidence / 100 if confidence > 100 else confidence)  # Normalize if needed
            bar_chart_data["colors"].append(emotion_colors.get(dominant_emotion, "rgba(0, 0, 0, 0.65)"))
            bar_chart_data["question_mapping"][f"Q{i+1}"] = {
                "emotion": dominant_emotion,
                "confidence": confidence / 100 if confidence > 100 else confidence
            }
        else:
            bar_chart_data["question_mapping"][f"Q{i+1}"] = {"emotion": "Unknown", "confidence": 0}

    return bar_chart_data

def generate_report(evaluation_json_file, fused_emotion_json_file):
    eval_data = parse_evaluation_json(evaluation_json_file)
    emotion_data = parse_fused_emotion_json(fused_emotion_json_file)

    # Merge emotion data into questions
    for i, question in enumerate(eval_data["questions"]):
        question_num = f"Q{i+1}"
        emotion_info = emotion_data["question_mapping"].get(question_num, {"emotion": "Unknown", "confidence": 0})
        question["emotion"] = emotion_info["emotion"]
        question["emotion_confidence"] = emotion_info["confidence"]

    eval_data["barChartData"] = {
        "labels": emotion_data["labels"],
        "scores": emotion_data["scores"],
        "colors": emotion_data["colors"]
    }

    # Enhanced HTML Template
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Interview Report</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0/dist/chartjs-plugin-datalabels.min.js"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f0f2f5;
                color: #333;
            }
            .container {
                max-width: 900px;
                margin: 40px auto;
                background: #ffffff;
                border-radius: 15px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                padding: 30px;
                overflow: hidden;
            }
            .header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 30px;
                border-bottom: 2px solid #e0e0e0;
                padding-bottom: 20px;
            }
            .header .logo {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                background: #ddd;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2em;
                color: #666;
            }
            .header .details {
                text-align: right;
            }
            .header .details strong {
                font-size: 1.5em;
                color: #2c3e50;
            }
            .header .details .score {
                font-size: 1.2em;
                color: #27ae60;
                margin-top: 10px;
            }
            .chart-container {
                margin: 30px 0;
                background: #fff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            .questions {
                margin-top: 40px;
            }
            .questions h3 {
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            .table-container {
                overflow-x: auto;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background: #fff;
            }
            th, td {
                padding: 15px;
                text-align: left;
                border-bottom: 1px solid #ecf0f1;
            }
            th {
                background: #3498db;
                color: #fff;
                font-weight: 600;
            }
            td {
                vertical-align: top;
                font-size: 0.95em;
            }
            tr:nth-child(even) {
                background: #f9f9f9;
            }
            .emotion {
                font-weight: bold;
                color: #e74c3c;
            }
            .confidence {
                color: #7f8c8d;
                font-style: italic;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">Logo</div>
                <div class="details">
                    <strong>Interview Report</strong><br>
                    Date: May 15, 2025<br>
                </div>
            </div>
            <div class="chart-container">
                <h4>Emotion Distribution</h4>
                <canvas id="barChart"></canvas>
            </div>
            <div class="chart-container">
                <h4>Performance Scores</h4>
                <canvas id="stackedBarChart"></canvas>
            </div>
            <div class="questions">
                <h3>Question Responses</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Question</th>
                                <th>Answer</th>
                                <th>Feedback</th>
                                <th>Emotion</th>
                                <th>Confidence</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>
        <script>
            const data = {json_data};

            // Populate Questions Table
            const tableBody = document.querySelector('.table-container tbody');
            tableBody.innerHTML = '';
            data.questions.forEach((item) => {
                const feedbackText = item.feedback.split("Feedback:")[1]?.trim() || "None";
                const row = `<tr>
                    <td>${item.question}</td>
                    <td>${item.answer}</td>
                    <td>${feedbackText}</td>
                    <td class="emotion">${item.emotion}</td>
                    <td class="confidence">${item.emotion_confidence.toFixed(2)}</td>
                </tr>`;
                tableBody.innerHTML += row;
            });

            // Bar Chart for Emotions
            const barCtx = document.getElementById('barChart').getContext('2d');
            new Chart(barCtx, {
                type: 'bar',
                data: {
                    labels: data.barChartData.labels,
                    datasets: [{
                        label: 'Emotion Confidence',
                        data: data.barChartData.scores,
                        backgroundColor: data.barChartData.colors,
                        borderColor: data.barChartData.colors,
                        borderWidth: 1,
                        borderRadius: 10
                    }]
                },
                options: {
                    scales: { y: { beginAtZero: true, title: { display: true, text: 'Confidence' } } },
                    plugins: {
                        legend: { display: false },
                        datalabels: {
                            color: '#fff',
                            font: { weight: 'bold' },
                            formatter: (value, ctx) => data.barChartData.labels[ctx.dataIndex]
                        }
                    }
                }
            });

            // Stacked Bar Chart for Scores
            const stackedCtx = document.getElementById('stackedBarChart').getContext('2d');
            new Chart(stackedCtx, {
                type: 'bar',
                data: {
                    labels: data.stackedBarChartData.labels,
                    datasets: data.stackedBarChartData.datasets.map((dataset, index) => ({
                        ...dataset,
                        backgroundColor: ['#6ce5e8', '#41b8d5', '#2d8bba'][index],
                        borderRadius: 10
                    }))
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    plugins: { legend: { position: 'top' } },
                    scales: { x: { stacked: true, beginAtZero: true, title: { display: true, text: 'Score' } }, y: { stacked: true } }
                }
            });
        </script>
    </body>
    </html>
    """

    # Embed JSON Data
    html_with_data = html_template.replace("{json_data}", json.dumps(eval_data))

    # Save to File
    with open("session/report/interview_report.html", "w") as file:
        file.write(html_with_data)

if __name__ == "__main__":
    generate_report("session/evaluation_results.json", "session/fused_emotion_predictions.json")