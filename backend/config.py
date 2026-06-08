"""
Configuration — API Keys & Settings
=====================================
⚠️  CHANGE THESE BEFORE RUNNING  ⚠️

1. GROQ_API_KEY     → Get free key at: https://console.groq.com/keys
2. DEEPGRAM_API_KEY → Get free key at: https://console.deepgram.com  (1000 free credits)

Do NOT commit this file to Git if you add real keys.
Add config.py to .gitignore or use a .env file instead.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # loads from .env file if present

# ──────────────────────────────────────────────
#  🔑  API KEYS  — CHANGE THESE
# ──────────────────────────────────────────────

# Groq (free tier, fast LLM inference)
# Sign up: https://console.groq.com/keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")

# Deepgram (Speech-to-Text + Text-to-Speech, 1000 free credits)
# Sign up: https://console.deepgram.com
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "YOUR_DEEPGRAM_API_KEY_HERE")

# ──────────────────────────────────────────────
#  🤖  LLM SETTINGS  — OPTIONAL TUNING
# ──────────────────────────────────────────────

# Groq model to use for interview logic
# Options: "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Max tokens for LLM responses
MAX_TOKENS = 1024

# ──────────────────────────────────────────────
#  🎤  AUDIO SETTINGS
# ──────────────────────────────────────────────

# Deepgram STT model — "nova-2" is best quality on free tier
DEEPGRAM_STT_MODEL = "nova-2"

# Deepgram TTS voice
# Options: "aura-asteria-en" (female), "aura-orion-en" (male), "aura-luna-en" (female soft)
DEEPGRAM_TTS_VOICE = "aura-orion-en"

# ──────────────────────────────────────────────
#  📁  UPLOAD SETTINGS
# ──────────────────────────────────────────────

UPLOAD_DIR = "uploads"
MAX_RESUME_SIZE_MB = 5
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# ──────────────────────────────────────────────
#  🎯  INTERVIEW SETTINGS
# ──────────────────────────────────────────────

# Number of questions per interview session
TOTAL_QUESTIONS = 10

# Mix of question types
QUESTION_MIX = {
    "technical": 5,      # Based on skills/projects in resume
    "behavioral": 3,     # STAR-based soft skill questions
    "situational": 2,    # Hypothetical scenarios
}

# Scoring weights
SCORING_WEIGHTS = {
    "relevance": 0.35,
    "depth": 0.30,
    "communication": 0.20,
    "confidence": 0.15,
}
