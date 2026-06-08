"""
Session Manager
================
In-memory session store for interview sessions.
Stores: resume data, question bank, conversation history, scores.

For production: replace with Redis or a database.
"""

import uuid
from typing import Optional
from datetime import datetime


# In-memory store: session_id -> session_data
_sessions: dict = {}


def create_session(resume_data: dict, question_bank: list) -> str:
    """Create a new interview session and return its ID."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "resume_data": resume_data,
        "question_bank": question_bank,
        "current_question_index": 0,
        "conversation_history": [],  # [{role, content}]
        "qa_history": [],            # [{question, answer, score, evaluation}]
        "scores": [],
        "mode": "interview",         # "interview" or "qa"
        "status": "active",          # "active", "completed"
        "follow_up_pending": False,
        "pending_follow_up": None,
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session by ID."""
    return _sessions.get(session_id)


def update_session(session_id: str, updates: dict):
    """Apply updates to a session."""
    if session_id in _sessions:
        _sessions[session_id].update(updates)


def add_qa_to_session(session_id: str, question: str, answer: str, score: float, evaluation: dict):
    """Append a Q&A pair with score to the session."""
    if session_id in _sessions:
        _sessions[session_id]["qa_history"].append({
            "question": question,
            "answer": answer,
            "score": score,
            "evaluation": evaluation,
        })
        _sessions[session_id]["scores"].append(score)


def add_message(session_id: str, role: str, content: str):
    """Add a message to conversation history."""
    if session_id in _sessions:
        _sessions[session_id]["conversation_history"].append({
            "role": role,
            "content": content
        })


def advance_question(session_id: str):
    """Move to the next question."""
    if session_id in _sessions:
        _sessions[session_id]["current_question_index"] += 1


def get_current_question(session_id: str) -> Optional[dict]:
    """Get the current question for a session."""
    session = get_session(session_id)
    if not session:
        return None
    idx = session["current_question_index"]
    bank = session["question_bank"]
    if idx < len(bank):
        return bank[idx]
    return None


def is_interview_complete(session_id: str) -> bool:
    """Check if all questions have been answered."""
    session = get_session(session_id)
    if not session:
        return True
    return session["current_question_index"] >= len(session["question_bank"])


def delete_session(session_id: str):
    """Delete a session."""
    _sessions.pop(session_id, None)
