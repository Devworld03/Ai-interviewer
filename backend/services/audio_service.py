"""
Audio Service — Deepgram STT + TTS
====================================
Speech-to-Text: Converts user voice recordings to text
Text-to-Speech: Converts AI interviewer responses to natural voice audio

Deepgram free tier: 1000 credits (~45+ hours of audio processing)
Sign up: https://console.deepgram.com
"""

import httpx
import base64
from config import DEEPGRAM_API_KEY, DEEPGRAM_STT_MODEL, DEEPGRAM_TTS_VOICE

DEEPGRAM_BASE_URL = "https://api.deepgram.com/v1"

HEADERS = {
    "Authorization": f"Token {DEEPGRAM_API_KEY}",
}


async def speech_to_text(audio_data: bytes, mimetype: str = "audio/webm") -> dict:
    """
    Convert audio bytes to text using Deepgram Nova-2 model.
    
    Args:
        audio_data: Raw audio bytes (webm, wav, mp3, etc.)
        mimetype: Audio MIME type
    
    Returns:
        dict with 'transcript', 'confidence', 'words'
    """
    url = f"{DEEPGRAM_BASE_URL}/listen"
    
    params = {
        "model": DEEPGRAM_STT_MODEL,
        "smart_format": "true",
        "punctuate": "true",
        "utterances": "false",
        "language": "en-US",
    }

    headers = {
        **HEADERS,
        "Content-Type": mimetype,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            params=params,
            headers=headers,
            content=audio_data,
        )
        response.raise_for_status()
        data = response.json()

    try:
        channel = data["results"]["channels"][0]
        alternative = channel["alternatives"][0]
        return {
            "transcript": alternative.get("transcript", ""),
            "confidence": alternative.get("confidence", 0),
            "words": alternative.get("words", []),
        }
    except (KeyError, IndexError):
        return {"transcript": "", "confidence": 0, "words": []}


async def text_to_speech(text: str) -> bytes:
    """
    Convert text to natural speech audio using Deepgram Aura TTS.
    
    Args:
        text: Text to convert to speech
    
    Returns:
        MP3 audio bytes
    """
    url = f"{DEEPGRAM_BASE_URL}/speak"
    
    params = {
        "model": DEEPGRAM_TTS_VOICE,
    }

    headers = {
        **HEADERS,
        "Content-Type": "application/json",
    }

    payload = {"text": text}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            params=params,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.content  # Returns MP3 bytes
