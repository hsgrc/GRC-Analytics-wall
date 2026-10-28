from __future__ import annotations

import re
import requests

from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


CASUAL = {
    "hello": "Hi! 😊 How can I help you today?",
    "hi": "Hi! 😊 How can I help you today?",
    "hey": "Hey! 😊 How can I help you today?",
    "hii": "Hi! 😊 How can I help you today?",
    "hiii": "Hi! 😊 How can I help you today?",
    "good morning": "Good morning! 😊 How can I help you today?",
    "good afternoon": "Good afternoon! 😊 How can I help you today?",
    "good evening": "Good evening! 😊 How can I help you today?",
    "good night": "Good night! 😊 Take care!",
    "thanks": "You're most welcome! 😊",
    "thank you": "You're most welcome! 😊",
    "thankyou": "You're most welcome! 😊",
    "thank u": "You're most welcome! 😊",
    "bye": "Goodbye! 😊 Have a great day!",
    "goodbye": "Goodbye! 😊 Have a great day!",
}


def norm(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text)


def casual_response(question: str) -> str | None:
    return CASUAL.get(norm(question))


def _language_instruction(language: str) -> str:
    instructions = {
        "Hindi": (
            "Respond entirely in Hindi using Devanagari script. "
            "Do not switch to English unless a proper name, "
            "product name, or necessary technical term must remain unchanged."
        ),
        "English": (
            "Respond entirely in English."
        ),
        "Hinglish": (
            "Respond naturally in Hinglish using Roman script, "
            "mixing Hindi and English in the way people commonly speak."
        ),
        "Marathi": (
            "Respond entirely in Marathi using Devanagari script."
        ),
        "Punjabi": (
            "Respond entirely in Punjabi using Gurmukhi script."
        ),
        "Tamil": (
            "Respond entirely in Tamil using Tamil script."
        ),
        "Telugu": (
            "Respond entirely in Telugu using Telugu script."
        ),
    }

    return instructions.get(
        str(language).strip(),
        instructions["Hindi"],
    )


def _call_ollama(
    question: str,
    context: str,
    language: str = "Hindi",
) -> str:

    language_instruction = _language_instruction(
        language
    )

    prompt = f"""Facts about GetRightCover:
{context}

Customer question:
{question}

Language requirement:
{language_instruction}

Answer the customer directly using only the facts above.
Start with the answer. Do not describe the question or the source.
Do not mention AI, Qwen, Ollama, prompts, instructions, context, retrieval, or internal systems.
Be natural, concise, and complete. If the customer asks for steps, use numbered steps.
Follow the requested language strictly.
Return only the customer-facing answer."""

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.0,
            "num_predict": 220,
        },
    }

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("message", {}).get("content", "").strip()


def clean(answer: str) -> str:
    # Normalize response whitespace at the source.
    # Remove invisible characters and leading indentation
    # from every line while preserving line breaks.
    answer = str(answer)
    answer = (
        answer
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u200b", "")
        .replace("\ufeff", "")
    )
    answer = re.sub(r"^[\\s\\u00A0\\u2007\\u202F]+", "", answer, flags=re.MULTILINE)
    answer = answer.strip().replace("```", "").strip()

    bad_markers = [
        "the user is asking",
        "the customer is asking",
        "we are given",
        "according to the",
        "looking at the",
        "first, i need",
        "based on the context",
    ]
    low = answer.lower()
    if any(low.startswith(m) for m in bad_markers):
        return ""
    return answer


def generate_answer(
    question: str,
    knowledge_context: str,
    language: str = "Hindi",
) -> str:

    casual = casual_response(question)
    if casual:
        return casual

    if not knowledge_context.strip():
        return "Sorry, I don't have verified information about that right now."

    try:
        answer = clean(
            _call_ollama(
                question,
                knowledge_context,
                language,
            )
        )
        if answer:
            return answer

        # Small fallback prompt if the model leaks meta-analysis.
        language_instruction = _language_instruction(
            language
        )

        fallback = (
            f"Facts:\n{knowledge_context}\n\n"
            f"Question:\n{question}\n\n"
            f"Language requirement:\n{language_instruction}\n\n"
            "Answer directly in the requested language only."
        )
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": fallback}],
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": {"temperature": 0.0, "num_predict": 220},
        }
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        answer = clean(response.json().get("message", {}).get("content", ""))
        return answer or "Sorry, I couldn't generate a response right now."

    except requests.ConnectionError:
        return "I'm having trouble connecting right now. Please try again."
    except requests.Timeout:
        return "It's taking a little longer than usual. Please try again."
    except requests.RequestException as exc:
        print(f"[ollama error] {exc}")
        return "I'm having trouble generating a response right now."
