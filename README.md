# ◆ InterviewAI — AI Mock Interview Platform

A powerful voice-based mock interview platform that analyzes your resume and conducts a personalized AI-driven interview with real-time scoring and feedback.

---

## 🚀 Features

- **Resume Upload & Analysis** — Supports PDF, DOCX, TXT. Groq LLM extracts structured data.
- **Personalized Question Generation** — 10 questions tailored to your exact resume (5 technical, 3 behavioral, 2 situational)
- **Voice Interview Mode** — Speak your answers; Deepgram Nova-2 transcribes in real-time
- **Text Interview Mode** — Type your answers with Ctrl+Enter shortcut
- **Real-time Evaluation** — Each answer is scored 0–10 with strengths and improvement points
- **AI Interviewer Voice** — Deepgram Aura TTS reads back the interviewer's responses
- **Ask Your Resume** — Free-form Q&A to get career insights from your resume
- **Comprehensive Report** — Final score, grade, hire recommendation, category breakdown, study resources

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | **FastAPI** + Python | REST API, routing, session management |
| LLM | **Groq** (Llama 3.3 70B) | Resume parsing, question generation, evaluation, scoring |
| STT | **Deepgram Nova-2** | Speech-to-Text (voice answers) |
| TTS | **Deepgram Aura** | Text-to-Speech (AI interviewer voice) |
| Frontend | Vanilla HTML/CSS/JS | Interview UI, voice recording, charts |
| File Parsing | PyPDF2, python-docx | Resume text extraction |

---

## ⚙️ Setup Guide

### Step 1: Get API Keys

#### Groq (Free — No credit card needed)
1. Go to **https://console.groq.com/keys**
2. Sign up / log in
3. Click **"Create API Key"**
4. Copy your key

#### Deepgram (1000 free credits — No credit card needed)
1. Go to **https://console.deepgram.com**
2. Sign up
3. Go to **API Keys** section
4. Create a new API key
5. Copy your key

---

### Step 2: Configure API Keys

**Option A — .env file (recommended)**

```bash
# In the project root (ai_interviewer/)
cp .env.example .env
```

Edit `.env`:
```env
GROQ_API_KEY=gsk_your_actual_groq_key_here
DEEPGRAM_API_KEY=your_actual_deepgram_key_here
```

**Option B — Edit config.py directly**

Open `backend/config.py` and replace:
```python
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"      # ← Replace this
DEEPGRAM_API_KEY = "YOUR_DEEPGRAM_API_KEY_HERE"  # ← Replace this
```

---

### Step 3: Install Dependencies

```bash
cd ai_interviewer/backend
pip install -r requirements.txt
```

---

### Step 4: Run the Server

```bash
cd ai_interviewer/backend
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Step 5: Open the App

Open your browser and go to:
```
http://localhost:8000
```

---

## 📁 Project Structure

```
ai_interviewer/
├── .env.example              ← Copy to .env and add your API keys
├── .gitignore
│
├── backend/
│   ├── main.py               ← FastAPI app entry point
│   ├── config.py             ← ⚠️ API keys & all settings HERE
│   ├── requirements.txt
│   │
│   ├── routes/
│   │   ├── resume.py         ← POST /api/resume/upload
│   │   ├── interview.py      ← POST /api/interview/start, /answer, /chat, /report
│   │   └── audio.py          ← POST /api/audio/stt, /tts
│   │
│   ├── services/
│   │   ├── resume_parser.py  ← PDF/DOCX/TXT extraction + LLM parsing
│   │   ├── interview_engine.py ← Question gen, answer eval, scoring, report
│   │   └── audio_service.py  ← Deepgram STT + TTS
│   │
│   └── utils/
│       └── session_manager.py ← In-memory session store
│
└── frontend/
    ├── templates/
    │   └── index.html        ← Main UI (5 screens)
    └── static/
        ├── css/style.css     ← All styles
        └── js/app.js         ← All frontend logic
```

---

## 🎛 Customization

### Change LLM Model
In `backend/config.py`:
```python
GROQ_MODEL = "llama-3.3-70b-versatile"  # Best quality
# GROQ_MODEL = "llama-3.1-8b-instant"   # Faster, lighter
# GROQ_MODEL = "mixtral-8x7b-32768"     # Alternative
```

### Change TTS Voice
In `backend/config.py`:
```python
DEEPGRAM_TTS_VOICE = "aura-orion-en"    # Male voice
# DEEPGRAM_TTS_VOICE = "aura-asteria-en"  # Female voice
# DEEPGRAM_TTS_VOICE = "aura-luna-en"     # Soft female
```

### Change Number of Questions
In `backend/config.py`:
```python
TOTAL_QUESTIONS = 10  # Change to any number

QUESTION_MIX = {
    "technical": 5,
    "behavioral": 3,
    "situational": 2,
}
```

### Change Scoring Weights
In `backend/config.py`:
```python
SCORING_WEIGHTS = {
    "relevance": 0.35,
    "depth": 0.30,
    "communication": 0.20,
    "confidence": 0.15,
}
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/resume/upload` | Upload resume, get session_id |
| GET | `/api/resume/{session_id}` | Get parsed resume data |
| POST | `/api/interview/start/{session_id}` | Start interview, get first question |
| POST | `/api/interview/answer/{session_id}` | Submit answer, get evaluation |
| POST | `/api/interview/chat/{session_id}` | Q&A about resume |
| GET | `/api/interview/report/{session_id}` | Get final report |
| POST | `/api/audio/stt` | Speech-to-Text |
| POST | `/api/audio/tts` | Text-to-Speech |

Interactive docs at: **http://localhost:8000/docs**

---

## 📊 Interview Flow

```
Upload Resume
    ↓
Parse with Groq LLM (extract skills, experience, projects)
    ↓
Generate 10 personalized questions
    ↓
Start Interview (voice or text)
    ↓
For each question:
    Candidate answers → STT transcription → LLM evaluation → Score + feedback
    ↓ (optional TTS reads AI response)
    ↓
After all questions:
    Generate comprehensive report
    (score, grade, hire rec, category breakdown, study resources)
```

---

## ⚠️ Notes

- Sessions are in-memory. Restarting the server clears all sessions.
- For production, replace `utils/session_manager.py` with Redis.
- Uploaded resume files are deleted immediately after parsing.
- TTS failures are non-blocking — the interview continues even if Deepgram TTS fails.

---

## 🐞 Common Issues

**"Module not found" errors**
```bash
pip install -r requirements.txt
```

**"Microphone access denied" in browser**
- Use `http://localhost:8000` (not a different IP)
- Allow microphone in browser permissions

**TTS not working**
- Check your Deepgram API key in `.env` or `config.py`
- Verify you have remaining credits at https://console.deepgram.com

**Groq rate limit**
- Free tier: 14,400 requests/day, 30 req/min
- If you hit limits, wait a minute or upgrade your plan
