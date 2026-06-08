"""
Resume Parser Service
======================
Extracts structured information from uploaded resumes (PDF, DOCX, TXT).
Uses Groq LLM to intelligently parse and structure resume content.
"""

import os
import json
import re
import PyPDF2
import docx
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, MAX_TOKENS


client = Groq(api_key=GROQ_API_KEY)


def extract_text_from_file(file_path: str) -> str:
    """Extract raw text from PDF, DOCX, or TXT file."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text

    elif ext == ".docx":
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def parse_resume_with_llm(raw_text: str) -> dict:
    """
    Use Groq LLM to extract structured data from resume text.
    Returns a dict with: name, email, skills, experience, education, projects, summary.
    """
    prompt = f"""
You are an expert resume parser. Extract structured information from the following resume text.

Return ONLY a valid JSON object with this exact structure:
{{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "phone number or null",
  "location": "city, country or null",
  "summary": "2-3 sentence professional summary",
  "skills": {{
    "technical": ["skill1", "skill2", ...],
    "soft": ["skill1", "skill2", ...]
  }},
  "experience": [
    {{
      "company": "Company Name",
      "role": "Job Title",
      "duration": "Jan 2022 - Present",
      "responsibilities": ["key responsibility 1", "key responsibility 2"],
      "technologies": ["tech1", "tech2"]
    }}
  ],
  "education": [
    {{
      "institution": "University Name",
      "degree": "Bachelor of Science in Computer Science",
      "year": "2020",
      "gpa": "3.8 or null"
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Brief description",
      "technologies": ["tech1", "tech2"],
      "impact": "quantifiable impact or key achievement"
    }}
  ],
  "certifications": ["cert1", "cert2"],
  "interview_focus_areas": ["area1", "area2", "area3"]
}}

For "interview_focus_areas", identify the 3-5 most important technical/skill areas to focus on during a job interview based on this resume.

Resume text:
{raw_text[:4000]}

Return ONLY the JSON, no markdown, no explanation.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=MAX_TOKENS,
        temperature=0.1,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return minimal structure
        return {
            "name": "Candidate",
            "email": "",
            "phone": None,
            "location": None,
            "summary": raw_text[:300],
            "skills": {"technical": [], "soft": []},
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
            "interview_focus_areas": ["General Technical Skills", "Problem Solving", "Communication"],
            "raw_text": raw_text[:2000]
        }


def parse_resume(file_path: str) -> dict:
    """Full pipeline: file → raw text → structured dict."""
    raw_text = extract_text_from_file(file_path)
    if not raw_text.strip():
        raise ValueError("Could not extract text from resume. Please check the file.")
    parsed = parse_resume_with_llm(raw_text)
    parsed["_raw_text"] = raw_text[:3000]  # keep raw for context
    return parsed
