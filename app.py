from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import fitz  # PyMuPDF
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()

# Initialize Firebase (path stored in .env file)
cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
firebase_admin.initialize_app(cred)
db = firestore.client()

def extract_text_from_pdf(file_path):
    text = ""
    doc = fitz.open(file_path)
    for page in doc:
        text += page.get_text()
    return text

def extract_keywords(text):
    keywords = ["python", "java", "react", "node", "sql", "aws", "c++", "machine learning"]
    return [kw for kw in keywords if kw.lower() in text.lower()]

@app.route("/upload", methods=["POST"])
def upload_resume():
    if 'resume' not in request.files or request.files['resume'].filename == '':
        return "No file uploaded", 400

    file = request.files['resume']
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file.save(tmp.name)
        text = extract_text_from_pdf(tmp.name)
        skills = extract_keywords(text)

    recommended = []
    for job in db.collection("jobs").stream():
        job_data = job.to_dict()
        required_skills = [s.lower() for s in job_data.get("skills", [])]
        if any(skill in required_skills for skill in skills):
            recommended.append(job_data)

    return jsonify({
        "extracted_skills": skills,
        "recommended_jobs": recommended
    })

@app.route("/add-job", methods=["POST"])
def add_job():
    title = request.form.get("title")
    description = request.form.get("description")
    skills_raw = request.form.get("skills")

    if not title or not description or not skills_raw:
        return "Missing job data", 400

    skills = [s.strip().lower() for s in skills_raw.split(",")]
    db.collection("jobs").add({
        "title": title,
        "description": description,
        "skills": skills
    })

    return "Job posted successfully", 200

if __name__ == "__main__":
    app.run(debug=True)
