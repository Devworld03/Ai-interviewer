"""
Interview Routes
=================
POST /api/interview/start/{session_id}   — Start interview, get first question
POST /api/interview/answer/{session_id}  — Submit answer, get evaluation + next question
POST /api/interview/chat/{session_id}    — Free Q&A about resume
GET  /api/interview/report/{session_id} — Get final interview report
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from services.interview_engine import (
    evaluate_response, generate_final_report, chat_with_resume
)
from utils.session_manager import (
    get_session, update_session, add_qa_to_session,
    add_message, advance_question, get_current_question,
    is_interview_complete
)

router = APIRouter()


class AnswerRequest(BaseModel):
    answer: str


class ChatRequest(BaseModel):
    message: str


@router.post("/start/{session_id}")
async def start_interview(session_id: str):
    """Start the interview and return the first question."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    question = get_current_question(session_id)
    if not question:
        raise HTTPException(status_code=400, detail="No questions available")

    name = session["resume_data"].get("name", "there")
    intro = (
        f"Welcome to your AI mock interview! I'm Alex, your interviewer today. "
        f"I've reviewed your resume carefully and prepared {len(session['question_bank'])} "
        f"personalized questions. We'll cover technical, behavioral, and situational topics. "
        f"Take your time with each answer. Let's begin!\n\n"
        f"Question 1: {question['question']}"
    )

    add_message(session_id, "assistant", intro)

    return JSONResponse({
        "success": True,
        "intro_message": intro,
        "question": question["question"],
        "question_number": 1,
        "total_questions": len(session["question_bank"]),
        "question_type": question.get("type", "general"),
        "focus_area": question.get("focus_area", ""),
    })


@router.post("/answer/{session_id}")
async def submit_answer(session_id: str, body: AnswerRequest):
    """Submit an answer, get evaluation and next question."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if is_interview_complete(session_id):
        return JSONResponse({
            "success": True,
            "interview_complete": True,
            "message": "Interview complete! Generating your report..."
        })

    current_question = get_current_question(session_id)
    if not current_question:
        raise HTTPException(status_code=400, detail="No current question found")

    answer = body.answer.strip()
    if not answer:
        raise HTTPException(status_code=400, detail="Answer cannot be empty")

    # Add to conversation history
    add_message(session_id, "user", answer)

    # Evaluate response
    evaluation = evaluate_response(
        current_question,
        answer,
        session["resume_data"],
        session["conversation_history"]
    )

    score = evaluation.get("overall_score", 5)

    # Save Q&A
    add_qa_to_session(
        session_id,
        current_question["question"],
        answer,
        score,
        evaluation
    )

    # Advance question
    advance_question(session_id)

    # Prepare response
    interviewer_response = evaluation.get("interviewer_response", "Good answer. Let's continue.")
    add_message(session_id, "assistant", interviewer_response)

    # Check if interview is done
    if is_interview_complete(session_id):
        outro = " That was the final question! You've completed your mock interview. Generating your comprehensive performance report now..."
        return JSONResponse({
            "success": True,
            "interview_complete": True,
            "interviewer_response": interviewer_response + outro,
            "score": score,
            "evaluation": {
                "strengths": evaluation.get("strengths", []),
                "improvements": evaluation.get("improvements", []),
            },
            "message": outro,
        })

    # Get next question
    next_question = get_current_question(session_id)
    session_updated = get_session(session_id)
    q_num = session_updated["current_question_index"] + 1
    total = len(session_updated["question_bank"])

    next_q_text = next_question["question"] if next_question else ""
    full_response = f"{interviewer_response}\n\nQuestion {q_num}: {next_q_text}"

    return JSONResponse({
        "success": True,
        "interview_complete": False,
        "interviewer_response": full_response,
        "score": score,
        "evaluation": {
            "strengths": evaluation.get("strengths", []),
            "improvements": evaluation.get("improvements", []),
        },
        "next_question": next_q_text,
        "question_number": q_num,
        "total_questions": total,
        "question_type": next_question.get("type", "general") if next_question else "",
        "focus_area": next_question.get("focus_area", "") if next_question else "",
    })


@router.get("/report/{session_id}")
async def get_report(session_id: str):
    """Generate and return the final interview report."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    qa_history = session.get("qa_history", [])
    scores = session.get("scores", [])

    if not qa_history:
        raise HTTPException(status_code=400, detail="No interview data found")

    report = generate_final_report(
        session["resume_data"],
        qa_history,
        scores
    )

    return JSONResponse({
        "success": True,
        "report": report,
        "candidate_name": session["resume_data"].get("name", "Candidate"),
        "total_questions": len(qa_history),
        "qa_history": [
            {
                "question": qa["question"],
                "answer": qa["answer"][:200] + "..." if len(qa["answer"]) > 200 else qa["answer"],
                "score": qa["score"]
            }
            for qa in qa_history
        ]
    })


@router.post("/chat/{session_id}")
async def chat_about_resume(session_id: str, body: ChatRequest):
    """Free-form Q&A about the resume."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    history = session.get("conversation_history", [])
    
    response = chat_with_resume(
        message,
        session["resume_data"],
        history
    )

    add_message(session_id, "user", message)
    add_message(session_id, "assistant", response)

    return JSONResponse({
        "success": True,
        "response": response
    })
