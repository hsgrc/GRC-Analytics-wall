from __future__ import annotations

import secrets
from typing import Any

from .customer_insights import (
    is_customer_360_question,
    is_report_request,
)


_ACTIONS = {
    "customer_report": {
        "title": "Generate Customer Report",
        "description": "Create an Excel report using your verified customer records.",
    },
    "renewal_followup": {
        "title": "Draft Renewal Follow-up",
        "description": "Prepare a renewal follow-up message from available expiry records. Nothing will be sent.",
    },
    "customer_360": {
        "title": "View Customer 360",
        "description": "Display a consolidated summary of your verified customer records.",
    },
}


def detect_requested_action(question: str) -> str | None:
    """Recognize only explicitly supported, deterministic action intents."""
    q = (question or "").casefold()

    # Check follow-up drafting before the general renewal/expiry intent.
    followup_phrases = (
        "draft renewal",
        "renewal follow-up",
        "renewal follow up",
        "renewal reminder message",
        "draft a reminder",
        "draft reminder",
        "prepare renewal message",
        "write renewal message",
        "follow-up message",
        "follow up message",
        "renewal message draft",
        "renewal ka message",
        "renewal reminder bana",
    )
    if any(phrase in q for phrase in followup_phrases):
        return "renewal_followup"

    if is_report_request(question):
        return "customer_report"

    if is_customer_360_question(question):
        return "customer_360"

    return None


def create_pending_action(
    session: dict[str, Any],
    action_type: str,
) -> dict[str, str]:
    """Store one single-use pending action in the current server-side session."""
    if action_type not in _ACTIONS:
        raise ValueError("Unsupported agent action.")

    action_info = _ACTIONS[action_type]
    pending = {
        "action_id": secrets.token_urlsafe(24),
        "type": action_type,
        "title": action_info["title"],
        "description": action_info["description"],
    }

    # A newer proposal replaces any older unapproved proposal.
    session["pending_agent_action"] = pending

    return {
        "action_id": pending["action_id"],
        "title": pending["title"],
        "description": pending["description"],
    }


def consume_pending_action(
    session: dict[str, Any],
    action_id: str,
) -> dict[str, str] | None:
    """Consume a proposal exactly once, only when its ID matches."""
    pending = session.get("pending_agent_action")
    if not isinstance(pending, dict):
        return None

    expected_id = str(pending.get("action_id") or "")
    if not expected_id or not action_id:
        return None

    if not secrets.compare_digest(expected_id, action_id):
        return None

    # Remove before execution to prevent replay of this approval.
    session.pop("pending_agent_action", None)

    action_type = str(pending.get("type") or "")
    action_info = _ACTIONS.get(action_type)
    if not action_info:
        return None

    return {
        "type": action_type,
        "title": action_info["title"],
        "description": action_info["description"],
    }
