import cv2
import numpy as np
from deepface import DeepFace
from mtcnn import MTCNN

# Initialize MTCNN for face detection
detector = MTCNN()

# Open webcam
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Convert to RGB
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Detect faces
    faces = detector.detect_faces(img_rgb)

    for face in faces:
        x, y, w, h = face['box']
        face_crop = img_rgb[y:y+h, x:x+w]

        if face_crop.size > 0:
            try:
                # Analyze emotion
                result = DeepFace.analyze(face_crop, actions=['emotion'], enforce_detection=False)
                emotion = result[0]['dominant_emotion']

                # Draw rectangle & display emotion
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, emotion, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            except:
                pass  # If DeepFace fails, continue

    # Show frame
    cv2.imshow("Real-Time Emotion Detection", frame)

    # Exit on pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
