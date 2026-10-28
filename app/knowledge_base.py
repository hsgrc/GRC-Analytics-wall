from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import KNOWLEDGE_FILE, MAX_CONTEXT_CHARS


@dataclass(frozen=True)
class Section:
    title: str
    content: str


def load_sections(path: Path = KNOWLEDGE_FILE) -> list[Section]:
    if not path.exists():
        raise FileNotFoundError(f"Knowledge file not found: {path}")

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: list[Section] = []

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        sections.append(Section(title, content))

    return sections


def normalize(text: str) -> str:
    t = text.lower()
    replacements = {
        "get right cover": "getrightcover",
        "get-right-cover": "getrightcover",
        "motor club": "motorclub",
        "2-wheeler": "2 wheeler",
        "two wheeler": "2 wheeler",
        "3-wheeler": "3 wheeler",
        "three wheeler": "3 wheeler",
        "4-wheeler": "4 wheeler",
        "four wheeler": "4 wheeler",
    }
    for old, new in replacements.items():
        t = t.replace(old, new)
    t = re.sub(r"[^\w₹\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def detect_intent(question: str) -> str:
    q = normalize(question)

    if any(x in q for x in ["benefit", "benefits", "included", "include", "what do i get"]):
        return "benefits"
    if any(x in q for x in ["renew", "renewal", "renewing"]):
        return "renewal"
    if any(x in q for x in ["purchase", "buy", "buying", "apply"]):
        return "purchase"
    if any(x in q for x in ["eligible", "eligibility", "requirement", "requirements"]):
        return "eligibility"
    if any(x in q for x in ["support", "contact", "phone", "email", "whatsapp", "help"]):
        return "support"
    if any(x in q for x in ["challan", "traffic challan", "fine"]):
        return "challan"
    if any(x in q for x in ["price", "pricing", "cost", "fee", "fees", "charge", "charges", "kitne ka", "kitna", "rupee", "rupees", "₹"]):
        return "pricing"
    if any(x in q for x in ["membership", "memberships", "plan", "plans", "type", "types", "available", "option", "options", "validity", "expire"]):
        return "plans"
    if re.search(r"\b(grc|getrightcover|getright|company|motorclub)\b", q):
        return "company"
    return "general"


def retrieve(question: str) -> tuple[str, list[str]]:
    sections = load_sections()
    if not sections:
        return "", []

    by_title = {s.title.lower(): s for s in sections}
    intent = detect_intent(question)

    wanted: list[str]
    if intent == "company":
        wanted = ["Company Overview", "What We Do", "Digital Platform"]
    elif intent == "plans":
        wanted = ["Membership Plans"]
    elif intent == "benefits":
        wanted = ["Membership Benefits"]
    elif intent == "pricing":
        wanted = ["Pricing", "Membership Plans"]
    elif intent == "renewal":
        wanted = ["Renewal Process"]
    elif intent == "purchase":
        wanted = ["Purchase Process"]
    elif intent == "eligibility":
        wanted = ["Eligibility"]
    elif intent == "support":
        wanted = ["Support"]
    elif intent == "challan":
        wanted = ["Traffic Challan Services"]
    else:
        wanted = ["Company Overview"]

    selected = [by_title[w.lower()] for w in wanted if w.lower() in by_title]
    if not selected:
        return "", []

    parts: list[str] = []
    total = 0
    for section in selected:
        remaining = MAX_CONTEXT_CHARS - total
        if remaining <= 0:
            break
        piece = section.content[:remaining]
        parts.append(piece)
        total += len(piece)

    return "\n\n---\n\n".join(parts), [s.title for s in selected]
