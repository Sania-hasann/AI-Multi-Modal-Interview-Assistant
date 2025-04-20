import json

def extract_scores(feedback):
    # Assuming scores are in the format "Accuracy Score: X/10"
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

        # Extract scores from feedback
        accuracy, clarity, preciseness = extract_scores(feedback)
        new_data["stackedBarChartData"]["labels"].append(f"Q{i+1}")
        new_data["stackedBarChartData"]["datasets"][0]["data"].append(accuracy)
        new_data["stackedBarChartData"]["datasets"][1]["data"].append(preciseness)
        new_data["stackedBarChartData"]["datasets"][2]["data"].append(clarity)

    return new_data

def parse_emotion_json(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    bar_chart_data = {
        "labels": [],
        "scores": [],
        "colors": []
    }
    emotion_colors = {
            "neutral": "rgba(150, 150, 150, 0.65)", # Darker Gray for neutral
            "angry": "rgba(220, 0, 0, 0.65)",        # Darker Red for anger
            "sad": "rgba(0, 0, 200, 0.65)",          # Darker Blue for sadness
            "fearful": "rgba(220, 140, 0, 0.65)",    # Darker Orange for fear
            "surprised": "rgba(255, 220, 0, 0.65)",  # Darker Yellow for surprise
            "disgust": "rgba(180, 0, 180, 0.65)"     # Darker Purple for disgust
        }
    for item in data:
        bar_chart_data["labels"].append(item["dominant_emotion"])
        bar_chart_data["scores"].append(item["confidence"])
        bar_chart_data["colors"].append(emotion_colors[item["dominant_emotion"]])
    return bar_chart_data

def generate_report(evaluation_json_file, emotion_json_file):

    data = parse_evaluation_json(evaluation_json_file)
    emotion_data = parse_emotion_json(emotion_json_file)

    data["barChartData"] = emotion_data

    # HTML Template with Placeholder
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PDF Replication</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                padding: 0;
                background-color: #f8f8f8;
            }
            .container {
                width: 800px;
                margin: auto;
                background: #fff;
                border: 1px solid #ccc;
                border-radius: 10px;
                padding: 20px;
            }
            .header {
                display: flex;
                align-items: center;
                margin-bottom: 20px;
            }
            .header img {
                width: 100px;
                height: 100px;
                border-radius: 50%;
                margin-right: 20px;
            }
            .header .details {
                font-size: 1.2em;
            }
            .bar-chart, .stacked-bar {
                margin: 20px 0;
            }
            .questions {
                margin-top: 30px;
                border-top: 1px solid #ccc;
                padding-top: 20px;
            }
            .table-container {
                margin-top: 20px;
                overflow-x: auto;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }
            th, td {
                border: 1px solid #CCCCFF;
                padding: 10px;
                text-align: left;
                vertical-align: top;
            }
            th {
                background-color: #CCCCFF;
                font-weight: bold;
            }
            td {
                font-size: 0.9em;
                line-height: 1.4;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="person-placeholder.png" alt="Person Image">
                <div class="details">
                    <strong>Full Name</strong><br>
                    Date of Interview: December 10, 2024<br>
                    <strong>58%</strong> Cumulative AI Score
                </div>
            </div>
            <div class="bar-chart">
                <canvas id="barChart"></canvas>
            </div>
            <div class="stacked-bar">
                <canvas id="stackedBarChart"></canvas>
            </div>
            <div class="questions">
                <h3>Question Answers</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Question</th>
                                <th>Answer</th>
                                <th>Feedback</th>
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
                let feedbackText = "None"; // Default value

                const feedbackIndex = item.feedback.toLowerCase().indexOf("feedback:");
                if (feedbackIndex !== -1) {
                    let extractedText = item.feedback.substring(feedbackIndex + 9);

                    // More robust "empty" check:
                    if (extractedText.trim().length > 0) {
                        feedbackText = extractedText.trim();
                    }
                }

                const row = `<tr>
                    <td>${item.question}</td>
                    <td>${item.answer}</td>
                    <td>${feedbackText}</td>
                </tr>`;
                tableBody.innerHTML += row;
            });

            // Bar Chart
            const barCtx = document.getElementById('barChart').getContext('2d');
            new Chart(barCtx, {
                type: 'bar',
                data: {
                    labels: data.barChartData.labels,
                    datasets: [{
                        label: '', // Empty label to avoid default legend
                        data: data.barChartData.scores,
                        backgroundColor: data.barChartData.colors,
                        borderColor: data.barChartData.colors,
                        borderWidth: 1,
                        borderRadius: 20
                    }]
                    
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        datalabels: {
                            color: 'black',
                            font: {
                                weight: 'bold'
                            },
                            formatter: (value, context) => {
                                return data.barChartData.labels[context.dataIndex];
                            }
                        }
                    }
                }
            });

            // Stacked Bar Chart
    const stackedCtx = document.getElementById('stackedBarChart').getContext('2d');
    new Chart(stackedCtx, {
        type: 'bar',
        data: {
            labels: data.stackedBarChartData.labels,
            datasets: data.stackedBarChartData.datasets.map((dataset, index) => {
                let backgroundColor;
                // Define different colors for each dataset
                switch (index) {
                    case 0:
                        backgroundColor = 'rgba(108, 229, 232, 1)'; // Accuracy color
                        break;
                    case 1:
                        backgroundColor = 'rgba(65, 184, 213, 1)'; // Preciseness color
                        break;
                    case 2:
                        backgroundColor = 'rgba(45, 139, 186, 1)'; // Clarity color
                        break;
                    default:
                        backgroundColor = 'rgba(0, 0, 0, 0.1)'; // Default color
                }
                return {
                    ...dataset,
                    backgroundColor: backgroundColor, // Assign the specific color
                    borderRadius: 10
                };
            })
        },
        options: {
            indexAxis: 'y', // Horizontal bars
            responsive: true,
            plugins: {
                legend: {
                    position: 'top'
                }
            },
            scales: {
                x: { stacked: true, beginAtZero: true },
                y: { stacked: true }
            }
        }
    });

        </script>
    </body>
    </html>
    """

    # Embed JSON Data
    html_with_data = html_template.replace("{json_data}", json.dumps(data))

    # Save to File
    with open("output.html", "w") as file:
        file.write(html_with_data)


if __name__ == "__main__":
    generate_report("evaluation_results.json", "emotion_predictions_multiple.json")