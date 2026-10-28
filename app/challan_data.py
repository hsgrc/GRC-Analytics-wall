from __future__ import annotations

import re
from datetime import date, datetime
from functools import lru_cache
from typing import Any

from .mongo_db import get_mongo_db


def normalize_challan_vehicle(value: Any) -> str:
    """Normalize a vehicle registration for matching."""
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _vehicle_regex(value: Any) -> str:
    """Build a case-insensitive regex that tolerates spaces and punctuation."""
    normalized = normalize_challan_vehicle(value)
    if not normalized:
        return r"(?!)"

    return (
        r"^\s*"
        + r"[^A-Z0-9]*".join(re.escape(char) for char in normalized)
        + r"[^A-Z0-9]*$"
    )


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    text = str(value).strip()
    return text or None


def _nonempty(*values: Any) -> Any:
    for value in values:
        if value is not None and str(value).strip():
            return value
    return None


def get_vehicle_challans(vehicle_number: str) -> list[dict[str, Any]]:
    """
    Return individual challan records for one exact normalized vehicle.
    Data is read live from MongoDB. Caller must verify vehicle ownership
    before returning these records to a customer.
    """
    key = normalize_challan_vehicle(vehicle_number)
    if not key:
        return []

    db = get_mongo_db()
    pattern = _vehicle_regex(vehicle_number)
    records: list[dict[str, Any]] = []

    # Traffic challan records and their nested source details.
    for doc in db.challans.find(
        {
            "vehicleNumber": {"$regex": pattern, "$options": "i"},
            "isDeleted": {"$ne": True},
        },
        {
            "vehicleNumber": 1,
            "challanData": 1,
            "isActive": 1,
            "created_at": 1,
        },
    ):
        nested_items = doc.get("challanData") or []

        for item in nested_items:
            if not isinstance(item, dict):
                continue

            challan_number = _nonempty(
                item.get("challanNo"),
                item.get("rcNo"),
            )
            if challan_number is None:
                continue

            records.append({
                "type": "E-Challan",
                "challan_number": str(challan_number).strip(),
                "date_time": _date_text(item.get("dateChallan") or doc.get("created_at")),
                "payment_status": _nonempty(item.get("status")),
                "amount": _nonempty(
                    item.get("amountChallan"),
                    item.get("amountACF"),
                ),
            })

    # Operational challan-entry records. Classification uses courtType.
    for doc in db.challanentries.find(
        {
            "vehicleNumber": {"$regex": pattern, "$options": "i"},
            "isDeleted": {"$ne": True},
        },
        {
            "vehicleNumber": 1,
            "challanNumber": 1,
            "challanData": 1,
            "courtType": 1,
            "amount": 1,
            "paymentStatus": 1,
            "status": 1,
            "offenceDate": 1,
            "created_at": 1,
        },
    ):
        nested = doc.get("challanData") or {}
        if not isinstance(nested, dict):
            nested = {}

        challan_number = _nonempty(
            doc.get("challanNumber"),
            nested.get("challan_no"),
        )
        if challan_number is None:
            continue

        category = str(doc.get("courtType") or "").strip().casefold()
        if "court" in category:
            kind = "Court"
        elif "e-challan" in category or category == "echallan":
            kind = "E-Challan"
        else:
            kind = "Challan"

        records.append({
            "type": kind,
            "challan_number": str(challan_number).strip(),
            "date_time": _date_text(
                _nonempty(
                    nested.get("challan_date_time"),
                    doc.get("offenceDate"),
                    doc.get("created_at"),
                )
            ),
            "payment_status": _nonempty(
                doc.get("paymentStatus"),
                doc.get("status"),
                nested.get("challan_status"),
            ),
            "amount": _nonempty(
                doc.get("amount"),
                nested.get("amount_of_fine_imposed"),
                nested.get("fine_imposed"),
            ),
        })

    # Avoid duplicate rows when the same type and challan number appear
    # in both MongoDB sources.
    unique_records: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        dedupe_key = (
            str(record.get("type") or ""),
            str(record.get("challan_number") or "").casefold(),
        )
        if dedupe_key not in unique_records:
            unique_records[dedupe_key] = record

    return sorted(
        unique_records.values(),
        key=lambda row: (
            str(row.get("date_time") or ""),
            str(row.get("challan_number") or ""),
        ),
        reverse=True,
    )


def get_challan_index_counts() -> dict[str, int]:
    """Return database-backed counts for diagnostics."""
    db = get_mongo_db()

    e_challan_pipeline = [
        {"$match": {"isDeleted": {"$ne": True}, "challanData": {"$type": "array"}}},
        {"$unwind": "$challanData"},
        {"$match": {"challanData.challanNo": {"$exists": True, "$nin": [None, ""]}}},
        {"$count": "total"},
    ]
    e_result = list(db.challans.aggregate(e_challan_pipeline, maxTimeMS=15000))
    e_challans = e_result[0]["total"] if e_result else 0

    court_challans = db.challanentries.count_documents({
        "isDeleted": {"$ne": True},
        "courtType": {"$regex": "court", "$options": "i"},
        "challanNumber": {"$nin": [None, ""]},
    })

    e_entry_challans = db.challanentries.count_documents({
        "isDeleted": {"$ne": True},
        "courtType": {"$regex": "e-challan", "$options": "i"},
        "challanNumber": {"$nin": [None, ""]},
    })

    return {
        "indexed_vehicles": db.challans.distinct("vehicleNumber").__len__(),
        "court_records": court_challans,
        "e_challan_records": e_challans + e_entry_challans,
    }
