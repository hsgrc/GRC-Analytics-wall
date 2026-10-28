from __future__ import annotations

import base64
import subprocess
import tempfile
from pathlib import Path

from .config import BASE_DIR
from .knowledge_base import retrieve
from .llm import generate_answer


# =========================================================
# MODELS
# =========================================================

WHISPER_MODEL = "mlx-community/whisper-tiny-mlx"

PIPER_MODEL = (
    BASE_DIR
    / "hi_IN-priyamvada-medium.onnx"
)


# =========================================================
# LANGUAGE MAP
# =========================================================

WHISPER_LANGUAGE = {
    "English": "en",
    "Hindi": "hi",
    "Hinglish": None,
    "Marathi": "mr",
    "Gujarati": "gu",
    "Punjabi": "pa",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te",
}


# =========================================================
# CONVERT UPLOADED AUDIO TO WAV
# =========================================================

def convert_to_wav(
    input_path: Path,
    output_path: Path,
) -> None:

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-sample_fmt",
        "s16",
        str(output_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            "FFmpeg could not process the audio:\n"
            + result.stderr[-2000:]
        )


# =========================================================
# SPEECH TO TEXT
# =========================================================

def transcribe_audio(
    audio_path: Path,
    language: str,
) -> str:

    language_code = WHISPER_LANGUAGE.get(
        language
    )


    output_dir = Path(
        tempfile.mkdtemp(
            prefix="grc_whisper_"
        )
    )


    command = [
        "mlx_whisper",
        str(audio_path),
        "--model",
        WHISPER_MODEL,
        "--output-dir",
        str(output_dir),
        "--output-format",
        "txt",
    ]


    if language_code:

        command.extend([
            "--language",
            language_code,
        ])


    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )


    if result.returncode != 0:

        raise RuntimeError(
            "Whisper transcription failed:\n"
            + result.stderr[-3000:]
        )


    transcript_file = (
        output_dir
        / f"{audio_path.stem}.txt"
    )


    if transcript_file.exists():

        transcript = (
            transcript_file
            .read_text(
                encoding="utf-8"
            )
            .strip()
        )

    else:

        # Fallback: mlx-whisper may return text
        # directly in stdout in some versions.
        transcript = (
            result.stdout
            .strip()
        )


    if not transcript:

        raise RuntimeError(
            "No speech detected in the audio."
        )


    return transcript


# =========================================================
# TEXT RESPONSE
# =========================================================

def generate_voice_answer(
    transcript: str,
    language: str,
) -> str:

    context, _ = retrieve(
        transcript
    )


    language_instruction = (
        f"Answer naturally in {language}."
    )


    question_for_llm = f"""
{language_instruction}

Customer said:
{transcript}

Give a concise, natural customer-support response.
Do not mention AI, models, prompts, internal systems,
knowledge bases or reasoning.
""".strip()


    answer = generate_answer(
        question_for_llm,
        context,
    )


    return answer.strip()


# =========================================================
# TEXT TO SPEECH
# =========================================================

def synthesize_speech(
    text: str,
) -> Path:

    output_path = Path(
        tempfile.mktemp(
            prefix="grc_tts_",
            suffix=".wav",
        )
    )


    if not PIPER_MODEL.exists():

        raise FileNotFoundError(
            f"Piper model not found: {PIPER_MODEL}"
        )


    command = [
        "python",
        "-m",
        "piper",

        "-m",
        str(PIPER_MODEL),

        "-f",
        str(output_path),

        "--",
        text,
    ]


    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )


    if result.returncode != 0:

        raise RuntimeError(
            "Piper speech generation failed:\n"
            + (
                result.stderr[-3000:]
                if result.stderr
                else result.stdout[-3000:]
            )
        )


    if not output_path.exists():

        raise RuntimeError(
            "Piper did not create the audio file."
        )


    return output_path


# =========================================================
# COMPLETE VOICE PIPELINE
# =========================================================

def process_voice_message(
    uploaded_audio: Path,
    language: str,
) -> dict:

    with tempfile.TemporaryDirectory(
        prefix="grc_voice_"
    ) as temp_dir:

        temp_dir_path = Path(
            temp_dir
        )


        # -------------------------------------------------
        # STEP 1
        # Uploaded browser audio
        # -> 16 kHz mono WAV
        # -------------------------------------------------

        wav_path = (
            temp_dir_path
            / "input.wav"
        )


        convert_to_wav(
            uploaded_audio,
            wav_path,
        )


        # -------------------------------------------------
        # STEP 2
        # Whisper
        # -------------------------------------------------

        transcript = transcribe_audio(
            wav_path,
            language,
        )


        # -------------------------------------------------
        # STEP 3
        # Qwen + GRC knowledge
        # -------------------------------------------------

        answer = generate_voice_answer(
            transcript,
            language,
        )


        # -------------------------------------------------
        # STEP 4
        # Piper
        # -------------------------------------------------

        speech_path = synthesize_speech(
            answer
        )


        # -------------------------------------------------
        # STEP 5
        # WAV -> Base64
        # -------------------------------------------------

        audio_bytes = (
            speech_path
            .read_bytes()
        )


        audio_base64 = base64.b64encode(
            audio_bytes
        ).decode("utf-8")


        return {
            "transcript": transcript,
            "answer": answer,
            "audio_base64": audio_base64,
            "audio_mime": "audio/wav",
        }
