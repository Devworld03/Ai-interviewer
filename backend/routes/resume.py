"""
Resume Routes
==============
POST /api/resume/upload  — Upload and parse resume file
GET  /api/resume/{session_id}  — Get parsed resume data
"""

import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from services.resume_parser import parse_resume
from services.interview_engine import generate_question_bank
from utils.session_manager import create_session
from config import UPLOAD_DIR, MAX_RESUME_SIZE_MB, ALLOWED_EXTENSIONS

router = APIRouter()

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload a resume file (PDF, DOCX, or TXT).
    Parses the resume and generates a personalized question bank.
    Returns a session_id for the interview.
    """
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Validate size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_RESUME_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb:.1f}MB). Max: {MAX_RESUME_SIZE_MB}MB"
        )

    # Save file
    safe_name = f"{os.urandom(8).hex()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # Parse resume
        resume_data = parse_resume(file_path)

        # Generate question bank
        question_bank = generate_question_bank(resume_data)

        # Create session
        session_id = create_session(resume_data, question_bank)

        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "candidate_name": resume_data.get("name", "Candidate"),
            "skills_detected": resume_data.get("skills", {}).get("technical", [])[:8],
            "focus_areas": resume_data.get("interview_focus_areas", []),
            "question_count": len(question_bank),
            "message": f"Resume parsed successfully! Ready to start your interview with {len(question_bank)} personalized questions."
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


@router.get("/{session_id}")
async def get_resume_data(session_id: str):
    """Get parsed resume data for a session."""
    from utils.session_manager import get_session
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    resume = session["resume_data"]
    # Don't send raw text to frontend
    safe_resume = {k: v for k, v in resume.items() if k != "_raw_text"}
    return JSONResponse({"success": True, "resume": safe_resume})
