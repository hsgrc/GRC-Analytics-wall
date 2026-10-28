from __future__ import annotations

import json
from difflib import SequenceMatcher
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import BASE_DIR


DATA_DIR = BASE_DIR / "data" / "GetRightCover_Chatbot_Data"


@lru_cache(maxsize=16)
def _load_json(filename: str) -> Any:
    path = DATA_DIR / filename

    if not path.is_file():
        raise FileNotFoundError(f"Dashboard data file is missing: {filename}")

    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _has(question: str, *terms: str) -> bool:
    normalized = _norm(question)
    padded_question = f" {normalized} "
    words = normalized.split()

    for term in terms:
        normalized_term = _norm(term)

        # Symbols such as currency signs may normalize to an empty string.
        if not normalized_term:
            continue

        if f" {normalized_term} " in padded_question:
            return True

        # Match simple plurals.
        plural = (
            normalized_term
            if normalized_term.endswith("s")
            else normalized_term + "s"
        )
        if f" {plural} " in padded_question:
            return True

        # Fuzzy match only longer, single-word terms to reduce false matches.
        if " " not in normalized_term and len(normalized_term) >= 6:
            variants = {normalized_term, plural}

            for word in words:
                if len(word) < 6:
                    continue

                for variant in variants:
                    if abs(len(word) - len(variant)) > 4:
                        continue

                    if SequenceMatcher(None, word, variant).ratio() >= 0.70:
                        return True

    return False


def _state_row(
    question: str,
    rows: list[dict[str, Any]],
    field: str,
) -> dict[str, Any] | None:
    """Find an explicitly mentioned state using whole-word matching."""
    q = f" {_norm(question)} "

    # Prefer longer names if a dataset includes overlapping state labels.
    candidates = sorted(
        rows,
        key=lambda row: len(_norm(row.get(field))),
        reverse=True,
    )

    for row in candidates:
        state = _norm(row.get(field))
        if state and f" {state} " in q:
            return row

    aliases = {
        "rajasthan": ("raj",),
        "uttar pradesh": ("up",),
        "madhya pradesh": ("mp",),
    }

    for state, state_aliases in aliases.items():
        if any(f" {alias} " in q for alias in state_aliases):
            for row in rows:
                if _norm(row.get(field)) == state:
                    return row

    return None


def is_dashboard_question(question: str) -> bool:
    """Identify questions that require internal dashboard records."""
    return _has(
        question,
        "dashboard", "vehicle", "vehicles", "gaadi", "gadi",
        "membership", "renewal", "expiry", "expire", "expired",
        "challan", "insurance", "puc", "fitness", "tax",
        "financier", "registered", "business partner",
        "claim", "rc status", "r c status", "violation",
    )


def answer_dashboard_question(
    question: str,
    language: str = "English",
) -> str | None:
    """
    Answer supported aggregate questions from dashboard summary JSONs.

    Returns None when this query layer cannot answer confidently.
    It deliberately does not expose customer contact details.
    """
    q = _norm(question)
    lang = _norm(language)

    portfolio = _load_json("vehicle_portfolio_summaries.json")
    renewals = _load_json("renewal_summaries.json")
    challans = _load_json("challan_summaries.json")
    insurance = _load_json("insurance_summaries.json")

    hindi = lang == "hindi"
    hinglish = lang == "hinglish"

    def say(en: str, hi: str, hl: str) -> str:
        if hindi:
            return hi
        if hinglish:
            return hl
        return en

    # -----------------------------------------------------
    # Vehicle portfolio: state-wise count
    # -----------------------------------------------------
    vehicle_terms = _has(
        q,
        "vehicle", "vehicles", "gaadi", "gadi", "vahano",
        "vehicle count", "number of vehicles",
    )
    state_vehicle_row = _state_row(
        question,
        portfolio.get("states", []),
        "STATE",
    )

    membership_terms = _has(
        q, "membership", "memberships", "renewal", "expiry",
        "expired", "expiring",
    )
    challan_terms = _has(q, "challan", "traffic fine", "violation")
    insurance_terms = _has(
        q, "insurance", "insurer", "insurance company"
    )

    if vehicle_terms and state_vehicle_row and not (
        membership_terms or challan_terms
    ):
        count = state_vehicle_row.get("total_vehicles")
        if isinstance(count, (int, float)):
            state = state_vehicle_row.get("STATE", "The selected state")
            return say(
                f"The vehicle portfolio summary records {int(count):,} vehicles for {state}.",
                f"वाहन पोर्टफोलियो सारांश के अनुसार {state} में {int(count):,} वाहन दर्ज हैं।",
                f"Vehicle portfolio summary ke according {state} mein {int(count):,} vehicles listed hain.",
            )

    # -----------------------------------------------------
    # Vehicle portfolio: total count
    # -----------------------------------------------------
    if vehicle_terms and not (
        membership_terms or challan_terms or insurance_terms
    ) and _has(
        q, "total", "overall", "all", "how many", "count", "number",
        "kitne", "kul", "total vehicles",
    ):
        total = portfolio.get("unique_compliance_rows")
        if isinstance(total, (int, float)):
            return say(
                f"The vehicle portfolio summary reports {int(total):,} unique compliance rows. This is the source's unique-compliance count, not necessarily the number of all raw rows.",
                f"वाहन पोर्टफोलियो सारांश में {int(total):,} यूनिक कंप्लायंस रिकॉर्ड दर्ज हैं। यह स्रोत का यूनिक-कंप्लायंस काउंट है, सभी raw rows की संख्या ज़रूरी नहीं।",
                f"Summary mein {int(total):,} unique compliance records hain. Ye source ka unique-compliance count hai, total raw rows zaroori nahi.",
            )

    # -----------------------------------------------------
    # Renewal/membership: state-wise summary
    # -----------------------------------------------------
    if membership_terms:
        renewal_state = _state_row(
            question,
            renewals.get("states", []),
            "label",
        )
        if renewal_state:
            value = renewal_state.get("value")
            if isinstance(value, (int, float)):
                state = renewal_state.get("label", "The selected state")
                return say(
                    f"The renewal summary reports {int(value):,} records for {state}.",
                    f"रिन्यूअल सारांश में {state} के लिए {int(value):,} रिकॉर्ड दर्ज हैं।",
                    f"Renewal summary mein {state} ke {int(value):,} records hain.",
                )

        category_fields = (
            ("status", ("status", "membership status")),
            ("expiry", ("expiry", "expired", "expiring")),
            ("membership_type", ("membership type", "direct", "business partner")),
            ("vehicle_type", ("vehicle type", "two wheeler", "2 wheeler", "three wheeler", "3 wheeler", "car", "truck")),
        )

        for key, terms in category_fields:
            if not _has(q, *terms):
                continue

            rows = renewals.get(key, [])
            found = next(
                (
                    row for row in rows
                    if _norm(row.get("label"))
                    and _norm(row.get("label")) in q
                ),
                None,
            )

            if found and isinstance(found.get("value"), (int, float)):
                label = found.get("label", key)
                value = int(found["value"])
                return say(
                    f"The renewal summary records {value:,} for {label}.",
                    f"रिन्यूअल सारांश में {label} के लिए {value:,} दर्ज हैं।",
                    f"Renewal summary mein {label} ke liye {value:,} records hain.",
                )

            if _has(q, "breakdown", "summary", "show all", "category wise"):
                items = [
                    f"- {row.get('label')}: {row.get('value')}"
                    for row in rows
                    if isinstance(row, dict)
                ]
                if items:
                    return "\n".join(items)

    # -----------------------------------------------------
    # Challans: state-wise aggregates
    # -----------------------------------------------------
    if challan_terms:
        state_row = _state_row(
            question,
            challans.get("states", []),
            "state_normalized",
        )

        if state_row:
            state = state_row.get("state_normalized", "Selected state")

            if _has(q, "amount", "rupee", "rupees", "₹", "fine amount", "total amount"):
                field = "Total_Amount"
                label = "challan amount"
            elif _has(q, "unique vehicle", "vehicles"):
                field = "Unique_Vehicles"
                label = "unique vehicles with challans"
            elif _has(q, "unpaid", "pending payment"):
                field = "Unpaid_Status"
                label = "unpaid challans"
            elif _has(q, "paid"):
                field = "Paid_Status"
                label = "paid challans"
            else:
                field = "Total_Challans"
                label = "challans"

            value = state_row.get(field)
            if isinstance(value, (int, float)):
                formatted = f"₹{value:,.0f}" if field == "Total_Amount" else f"{int(value):,}"
                return say(
                    f"The challan summary records {formatted} for {label} in {state}.",
                    f"चालान सारांश के अनुसार {state} में {label} की संख्या/राशि {formatted} है।",
                    f"Challan summary ke according {state} mein {label}: {formatted}.",
                )

        if _has(q, "total", "overall", "all", "how many", "count", "kitne", "kul"):
            crosscheck = challans.get("aggregate_crosscheck", {})
            total = crosscheck.get("monthly_total_challans_sum")
            if isinstance(total, (int, float)):
                return say(
                    f"The monthly challan-summary totals add up to {int(total):,} challans. This is a sum of the monthly summary rows.",
                    f"मासिक चालान सारांश की पंक्तियों का कुल योग {int(total):,} चालान है।",
                    f"Monthly challan summary rows ka total {int(total):,} challans hai.",
                )

        violations = challans.get("violations", [])
        for row in violations:
            violation = _norm(row.get("Violation_Clean"))
            if violation and violation in q:
                value = row.get("Total_Challans")
                if isinstance(value, (int, float)):
                    return say(
                        f"The challan summary records {int(value):,} challans for {row.get('Violation_Clean')}.",
                        f"चालान सारांश में {row.get('Violation_Clean')} के लिए {int(value):,} चालान दर्ज हैं।",
                        f"Challan summary mein {row.get('Violation_Clean')} ke {int(value):,} challans hain.",
                    )

    # -----------------------------------------------------
    # Insurance company summaries
    # -----------------------------------------------------
    if insurance_terms:
        dashboard = insurance.get("insurer_dashboard", [])
        matches = [
            row for row in dashboard
            if _norm(row.get("insurance_company"))
            and _norm(row.get("insurance_company")) in q
        ]

        if matches:
            row = matches[0]
            count = row.get("vehicle_count")
            if isinstance(count, (int, float)):
                return say(
                    f"The insurance summary associates {int(count):,} vehicles with {row.get('insurance_company')}.",
                    f"इंश्योरेंस सारांश में {row.get('insurance_company')} के साथ {int(count):,} वाहन दर्ज हैं।",
                    f"Insurance summary mein {row.get('insurance_company')} ke saath {int(count):,} vehicles hain.",
                )

        if _has(q, "most", "highest", "top", "largest", "sabse zyada"):
            ranked = sorted(
                (
                    row for row in dashboard
                    if isinstance(row.get("vehicle_count"), (int, float))
                ),
                key=lambda row: row["vehicle_count"],
                reverse=True,
            )
            if ranked:
                row = ranked[0]
                return say(
                    f"{row.get('insurance_company')} has the highest vehicle count in this insurance summary: {int(row['vehicle_count']):,}.",
                    f"इस इंश्योरेंस सारांश में सबसे अधिक वाहन {row.get('insurance_company')} के हैं: {int(row['vehicle_count']):,}।",
                    f"Is insurance summary mein sabse zyada vehicles {row.get('insurance_company')} ke hain: {int(row['vehicle_count']):,}.",
                )

    return None


def dashboard_data_available() -> bool:
    """Basic startup/test check for required summary files."""
    required = (
        "vehicle_portfolio_summaries.json",
        "renewal_summaries.json",
        "challan_summaries.json",
        "insurance_summaries.json",
    )
    return all((DATA_DIR / filename).is_file() for filename in required)
