"""
Audio Routes
=============
POST /api/audio/stt    — Convert audio to text (Speech-to-Text)
POST /api/audio/tts    — Convert text to audio (Text-to-Speech)
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from services.audio_service import speech_to_text, text_to_speech

router = APIRouter()


@router.post("/stt")
async def stt_endpoint(audio: UploadFile = File(...)):
    """
    Convert uploaded audio to text using Deepgram Nova-2 STT.
    
    Accepts: audio/webm, audio/wav, audio/mp3, audio/ogg
    Returns: { transcript, confidence }
    """
    content = await audio.read()
    
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Detect MIME type
    mimetype = audio.content_type or "audio/webm"

    try:
        result = await speech_to_text(content, mimetype)
        return JSONResponse({
            "success": True,
            "transcript": result["transcript"],
            "confidence": result["confidence"],
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {str(e)}")


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
async def tts_endpoint(body: TTSRequest):
    """
    Convert text to speech using Deepgram Aura TTS.
    
    Returns: MP3 audio bytes
    """
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # Limit TTS length
    if len(text) > 1000:
        text = text[:1000]

    try:
        audio_bytes = await text_to_speech(text)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=response.mp3"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")
