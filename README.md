# 🎓 ARGUS AI - Smart Exam Monitoring System

Argus AI is a real-time AI-powered system designed to detect cheating behaviors and unauthorized tools in physical exam halls using computer vision, facial recognition, and natural language analytics.

## 🔍 Problem
Manual invigilation is error-prone, inconsistent, and inefficient for large-scale exams. Traditional systems lack accuracy, real-time detection, and integration across tools and identity systems.

## ✅ Solution
ARGUS AI integrates:
- 🎯 **YOLOv8** for object and behavior detection  
- 🧠 **FaceNet** for identity verification and attendance logging  
- 📱 **Phone Detector** for identifying prohibited tools  
- 📦 **SQLite Database** for structured event storage  
- 🔎 **LangChain + RAG Assistant** for natural-language queries over logs  
- 🌐 **Django Web Interface** for live visualization, student stats, and smart reporting

## 🧱 System Architecture
- **Face Recognition**: Matches faces with student database (FaceNet + cosine similarity)
- **Cheating Detection**: Detects suspicious head movements and behavior (YOLO + ByteTrack)
- **Phone Detection**: Identifies mobile phones and logs incidents
- **Tracking**: Maintains persistent IDs across frames (ByteTrack)
- **Database**: Stores students, attendance, phone detections, and cheating events
- **Smart Assistant**: Uses RAG (LangChain + FAISS + Ollama) to answer natural language queries like:
  - “Who cheated the most?”
  - “Show Menna’s attendance summary”

## 📊 Evaluation
- YOLOv8 Accuracy: **94%**
- FaceNet Accuracy: **96.15%**
- Real-time speed on GPU: **30+ FPS**
- F1-Score (Cheating Classifier): **0.94**

## 🌍 Use Case
- Educational Institutions
- Government Exams
- Certification Bodies
- Offline-first or Privacy-sensitive Environments

## 🔐 Key Features
- Multi-person tracking with real-time feedback
- Screenshot capture of cheating moments
- Web interface for live alerts and records
- Smart Q&A interface using RAG assistant
- Privacy-conscious, edge-compatible architecture

## 🛠️ Tech Stack
- Python, OpenCV, TensorFlow/Keras, YOLOv8, ByteTrack, SQLite
- LangChain, FAISS, Ollama (LLM), MediaPipe
- Django (for web dashboard)

## 📁 Folder Structure
```

/models

* best.pt
* phone.pt
* facenet\_model.h5
  /database
* exam.db
  /web
* django\_dashboard/
  /scripts
* cheating\_detector.py
* face\_recognition.py
* phone\_detector.py
* rag\_assistant.py

```
## 📷screenshots
![Screenshot 2025-06-28 003948 1](https://github.com/user-attachments/assets/9f9b8635-5dea-4860-9893-fc23473c23b4)
![Screenshot 2025-06-28 004717 1](https://github.com/user-attachments/assets/8bf6d7c9-bd6a-451e-97ba-b5248366e649)
![Screenshot 2](https://github.com/user-attachments/assets/0d554b0f-707e-4f60-a17d-ead8cdb1d71e)
![image](https://github.com/user-attachments/assets/1fed8f8e-e89b-4847-81bc-168741619556)

## 🚀 Team
Ahmed Ghanem, Amr Khalafallah, Ahmed Saad, Mohamed Fawzy, Menna Allah, Mohamed Barakat, mohamed Khaled
**Supervisor**: Dr. Ahmed Kafafy – Faculty of Artificial Intelligence, Menoufia University

## 📅 Timeline
Spring 2025 – Final Year Graduation Project

---
https://www.canva.com/design/DAGrl-KGX7M/JL2DluGKPhMI08uPgdMh2A/edit?utm_content=DAGrl-KGX7M&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton
> “We believe modern education deserves modern protection. Argus AI brings integrity back to the exam hall.”
```
"# Monitoring-Student-Cheating-detetion-main" 
"# Monitoring-Student-Cheating-detetion-main" 
"# Monitoring-Student-Cheating-detetion-main" 
