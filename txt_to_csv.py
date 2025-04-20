import csv

def convert_txt_to_csv(txt_file, csv_file):
    """
    Converts a session history text file into a CSV file.
    Extracts questions and answers from the text file and saves them in separate columns.
    """
    questions = []
    answers = []

    # Read and parse the TXT file
    with open(txt_file, "r") as file:
        lines = file.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith("Question:"):
            questions.append(line.replace("Question: ", "").strip('"'))
        elif line.startswith("Answer:"):
            answers.append(line.replace("Answer: ", "").strip('"'))

    # Write to the CSV file
    with open(csv_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Question", "Answer"])
        writer.writerows(zip(questions, answers))

    print(f"Session history successfully saved to {csv_file}")
