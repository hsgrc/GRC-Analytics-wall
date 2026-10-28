from __future__ import annotations

import tempfile
from pathlib import Path

import requests

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    UI_FILE,
)

from .knowledge_base import (
    KNOWLEDGE_FILE,
    retrieve,
)

from .llm import generate_answer
from .voice import process_voice_message


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="GetRightCover Local Chatbot",
    version="1.0.0",
)


# =========================================================
# REQUEST / RESPONSE MODELS
# =========================================================

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000,
    )


class ChatResponse(BaseModel):
    answer: str


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return FileResponse(UI_FILE)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/api/health")
def health():

    try:

        r = requests.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=5,
        )

        ollama = r.ok

    except requests.RequestException:

        ollama = False

    return {
        "status": "ok",
        "ollama": ollama,
        "model": OLLAMA_MODEL,
        "knowledge_exists": KNOWLEDGE_FILE.exists(),
    }


# =========================================================
# NORMAL TEXT CHAT
# =========================================================

@app.post(
    "/api/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest):

    question = request.message.strip()

    try:

        context, _ = retrieve(
            question
        )

        answer = generate_answer(
            question,
            context,
        )

        return ChatResponse(
            answer=answer
        )

    except Exception as exc:

        print(
            f"[chat error] {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Chatbot could not "
                "process the request."
            ),
        )


# =========================================================
# LOCAL GRC LIVE
# =========================================================

@app.post("/api/voice-chat")
async def voice_chat(
    audio: UploadFile = File(...),
    language: str = Form("English"),
):

    temp_audio = None

    try:

        # -------------------------------------------------
        # Validate upload
        # -------------------------------------------------

        if not audio.filename:

            raise HTTPException(
                status_code=400,
                detail="No audio file was provided.",
            )


        # -------------------------------------------------
        # Save uploaded browser audio
        # -------------------------------------------------

        suffix = (
            Path(audio.filename).suffix
            or ".webm"
        )


        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            temp_audio = Path(
                temp_file.name
            )


            content = await audio.read()

            temp_file.write(
                content
            )


        # -------------------------------------------------
        # Whisper → Qwen → Piper
        # -------------------------------------------------

        result = process_voice_message(
            uploaded_audio=temp_audio,
            language=language,
        )


        return result


    except HTTPException:

        raise


    except Exception as exc:

        import traceback
        print(f"[voice-chat error] {exc}")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                "GRC Live could not process "
                "your voice message."
            ),
        )


    finally:

        # -------------------------------------------------
        # Cleanup uploaded temporary audio
        # -------------------------------------------------

        if temp_audio and temp_audio.exists():

            try:

                temp_audio.unlink()

            except OSError:

                pass