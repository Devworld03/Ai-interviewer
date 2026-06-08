"""
AI Interviewer Assistant - Main FastAPI Application
=====================================================
Entry point for the backend server.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import uvicorn
import os

from routes.interview import router as interview_router
from routes.audio import router as audio_router
from routes.resume import router as resume_router

app = FastAPI(
    title="AI Interviewer Assistant",
    description="Voice-based mock interview platform with resume-driven personalized question generation",
    version="1.0.0"
)

# CORS - allow all origins in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# Include routers
app.include_router(interview_router, prefix="/api/interview", tags=["Interview"])
app.include_router(audio_router, prefix="/api/audio", tags=["Audio"])
app.include_router(resume_router, prefix="/api/resume", tags=["Resume"])

# Serve frontend
from fastapi import Request
from fastapi.responses import HTMLResponse

templates = Jinja2Templates(directory="../frontend/templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
