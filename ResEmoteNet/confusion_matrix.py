import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load dataset
df = pd.read_csv("classification_scores_valid.csv")

# Extract true labels from the file path
df["true_label"] = df["filepath"].apply(lambda x: x.split("_")[-1].replace(".jpg", ""))

# Extract predicted labels (highest scoring emotion)
emotion_columns = ["happy", "surprise", "sadness", "anger", "disgust", "fear"]
df["predicted_label"] = df[emotion_columns].idxmax(axis=1)

# Compute confusion matrix
conf_matrix = pd.crosstab(df["true_label"], df["predicted_label"], rownames=['Actual'], colnames=['Predicted'])

# Plot confusion matrix
plt.figure(figsize=(8, 6))
sns.heatmap(conf_matrix, annot=True, fmt="d", cmap="Blues", linewidths=0.5, linecolor="white", square=True,
            cbar_kws={"shrink": 0.8}, annot_kws={"size": 12})

plt.title("Confusion Matrix", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Predicted Label", fontsize=12, labelpad=10)
plt.ylabel("Actual Label", fontsize=12, labelpad=10)
plt.xticks(fontsize=10, rotation=45)
plt.yticks(fontsize=10, rotation=0)

# Show plot
plt.show()
