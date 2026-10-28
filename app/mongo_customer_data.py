from __future__ import annotations

import re
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from .mongo_db import get_mongo_db


def normalize_phone(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))

    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    return digits if len(digits) == 10 else ""


def normalize_vehicle(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(str(value).strip())
    except (InvalidId, TypeError):
        return None


def _phone_regex(value: str) -> str:
    """Match a phone number with common punctuation and country prefixes."""
    digits = normalize_phone(value)

    if len(digits) != 10:
        return r"(?!)"

    separated_digits = r"\D*".join(re.escape(digit) for digit in digits)
    return r"^\D*(?:(?:91|0)\D*)?" + separated_digits + r"\D*$"


def get_customer_records(
    user_id: str,
    verified_mobile: str,
) -> dict[str, Any] | None:
    """
    Fetch customer records from live MongoDB.

    Only pass user_id and verified_mobile from a trusted, verified
    website identity. Never pass a user ID supplied by the browser.

    Memberships matched by phone are included only when that mobile
    belongs to exactly one user in the users collection.
    """
    db = get_mongo_db()
    oid = _object_id(user_id)
    mobile = normalize_phone(verified_mobile)

    if oid is None or not mobile:
        return None

    user = db.users.find_one(
        {"_id": oid, "isDeleted": {"$ne": True}},
        {
            "_id": 1,
            "name": 1,
            "mobileNumber": 1,
            "email": 1,
            "state": 1,
            "businessName": 1,
            "type": 1,
            "isActive": 1,
            "isDeleted": 1,
        },
    )

    if not user or normalize_phone(user.get("mobileNumber")) != mobile:
        return None

    # Check whether this phone belongs to exactly one user.
    matching_user_ids = []
    for row in db.users.find(
        {"mobileNumber": {"$type": "string"}},
        {"_id": 1, "mobileNumber": 1},
    ):
        if normalize_phone(row.get("mobileNumber")) == mobile:
            matching_user_ids.append(row["_id"])

    phone_is_unique = matching_user_ids == [oid]

    vehicle_projection = {
        "_id": 1,
        "customerId": 1,
        "vehicleNumber": 1,
        "make": 1,
        "model": 1,
        "vehicleType": 1,
        "vehicleClass": 1,
        "insuranceCompany": 1,
        "insuranceUpto": 1,
        "pucExpiry": 1,
        "fitnessUpto": 1,
        "taxUpto": 1,
        "permitUpto": 1,
        "registeredAt": 1,
        "vehicleStatus": 1,
        "blackList": 1,
        "isActive": 1,
        "isDeleted": 1,
    }

    vehicles = list(
        db.vehicledetails.find(
            {
                "customerId": oid,
                "isDeleted": {"$ne": True},
            },
            vehicle_projection,
        )
    )

    membership_query: dict[str, Any] = {
        "userId": oid,
        "phoneNumber": {"$type": "string"},
    }

    if phone_is_unique:
        membership_query = {
            "$or": [
                {"userId": oid},
                {"phoneNumber": {"$regex": _phone_regex(mobile)}},
            ]
        }

    memberships = list(
        db.memberships.find(
            membership_query,
            {
                "_id": 1,
                "userId": 1,
                "phoneNumber": 1,
                "name": 1,
                "certificateNumber": 1,
                "VehicleNumber": 1,
                "vehicleType": 1,
                "startDate": 1,
                "endDate": 1,
                "invoiceDate": 1,
                "state": 1,
            },
        )
    )

    claims = list(
        db.claims.find(
            {"userId": oid},
            {
                "_id": 1,
                "claimId": 1,
                "userId": 1,
                "vehicleDetails": 1,
                "claimStatus": 1,
                "paymentStatus": 1,
                "claimDetails": 1,
                "created_at": 1,
                "disputeDate": 1,
            },
        )
    )

    # Build vehicle registrations only from records linked to this user
    # or from uniquely phone-matched membership records.
    registrations: dict[str, str] = {}

    for row in vehicles:
        value = str(row.get("vehicleNumber") or "").strip()
        key = normalize_vehicle(value)
        if key:
            registrations.setdefault(key, value)

    for row in memberships:
        value = str(row.get("VehicleNumber") or "").strip()
        key = normalize_vehicle(value)
        if key:
            registrations.setdefault(key, value)

    vehicle_numbers = list(registrations.values())

    challan_query: dict[str, Any] = {
        "vehicleNumber": {"$in": vehicle_numbers}
    }

    if phone_is_unique:
        challan_query = {
            "$or": [
                {"vehicleNumber": {"$in": vehicle_numbers}},
                {"phoneNumber": {"$regex": _phone_regex(mobile)}},
            ]
        }

    challans = list(
        db.challans.find(
            challan_query,
            {
                "_id": 1,
                "vehicleNumber": 1,
                "challanData": 1,
                "isActive": 1,
                "isDeleted": 1,
                "created_at": 1,
            },
        )
    )

    challan_entries = list(
        db.challanentries.find(
            {"vehicleNumber": {"$in": vehicle_numbers}, "isDeleted": {"$ne": True}},
            {
                "_id": 1,
                "vehicleNumber": 1,
                "challanNumber": 1,
                "challanData": 1,
                "courtType": 1,
                "amount": 1,
                "paymentStatus": 1,
                "status": 1,
                "violation": 1,
                "state": 1,
                "created_at": 1,
                "updated_at": 1,
            },
        )
    )

    # Do not return the database user's private fields.
    return {
        "customer": {
            "customer_id": str(user["_id"]),
            "name": user.get("name"),
            "mobile": mobile,
            "email": user.get("email"),
            "state": user.get("state"),
            "business": user.get("businessName"),
            "type": user.get("type"),
        },
        "vehicles": vehicles,
        "memberships": memberships,
        "claims": claims,
        "challans": challans,
        "challan_entries": challan_entries,
        "membership_phone_fallback_used": phone_is_unique,
    }


def get_customer_snapshot(user_id: str) -> dict[str, Any] | None:
    """Build a customer snapshot from live MongoDB records."""
    from datetime import date, datetime

    db = get_mongo_db()
    oid = _object_id(user_id)
    if oid is None:
        return None

    user = db.users.find_one(
        {"_id": oid, "isDeleted": {"$ne": True}},
        {"_id": 1, "name": 1, "mobileNumber": 1, "email": 1,
         "state": 1, "businessName": 1, "type": 1},
    )
    if not user:
        return None

    mobile = normalize_phone(user.get("mobileNumber"))
    records = get_customer_records(str(oid), mobile)
    if not records:
        return None

    def show_date(value):
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value).strip() if value else None

    def document(label, value):
        expiry = show_date(value)
        status = "Date unavailable"
        if isinstance(value, (datetime, date)):
            day = value.date() if isinstance(value, datetime) else value
            remaining = (day - date.today()).days
            status = (
                f"Expired ({-remaining} days ago)" if remaining < 0
                else "Expires today" if remaining == 0
                else f"Expiring in {remaining} days" if remaining <= 30
                else f"Valid ({remaining} days remaining)"
            )
        return {"document": label, "expiry_date": expiry, "status": status}

    output = []
    for v in records["vehicles"]:
        reg = str(v.get("vehicleNumber") or "").strip()
        key = normalize_vehicle(reg)
        if not key:
            continue

        memberships = [
            m for m in records["memberships"]
            if normalize_vehicle(m.get("VehicleNumber")) == key
        ]
        claims = []
        for c in records["claims"]:
            details = c.get("vehicleDetails") or {}
            if normalize_vehicle(details.get("number")) == key:
                claims.append(c)

        raw = v.get("rawApiResponse") or {}
        if not isinstance(raw, dict):
            raw = {}

        output.append({
            "vehicle": {
                "vehicle_number": reg, "make": v.get("make"),
                "model": v.get("model"), "financier": raw.get("rcFinancer"),
                "registered_at": v.get("registeredAt"),
                "state": memberships[0].get("state") if memberships else user.get("state"),
                "insurance_company": v.get("insuranceCompany"),
            },
            "documents": [
                document("Insurance", v.get("insuranceUpto")),
                document("PUC", v.get("pucExpiry")),
                document("Fitness", v.get("fitnessUpto")),
                document("Tax", v.get("taxUpto")),
            ],
            "memberships": [
                {
                    "membership_type": "Membership",
                    "start_date": show_date(m.get("startDate")),
                    "end_date": show_date(m.get("endDate")),
                    "status": "Date available" if m.get("endDate") else "Date unavailable",
                    "expiry_bucket": None, "business_partner": None,
                    "vehicle_type": m.get("vehicleType"),
                } for m in memberships
            ],
            "renewal_claim_records": [
                {"claim_id": c.get("claimId"), "has_claim": True,
                 "claim_status": c.get("claimStatus"),
                 "payment_status": c.get("paymentStatus")}
                for c in claims
            ],
            "claim_indicator": {
                "matching_records": len(claims),
                "has_claim_flag": bool(claims),
            },
            "rc_statuses": [{"status": raw.get("rcStatus")}]
                if raw.get("rcStatus") else [],
            "customer_vehicle_links": [],
            "challan_data": {
                "individual_records_available": True,
                "note": "Challan records are read from MongoDB.",
            },
        })

    return {
        "customer": {
            "customer_id": str(oid), "name": user.get("name"),
            "mobile": mobile, "email": user.get("email"),
            "business": user.get("businessName"), "state": user.get("state"),
            "category": user.get("type"),
        },
        "vehicle_count_in_snapshot": len(output),
        "vehicles": output,
    }


def _vehicle_regex(value: Any) -> str:
    key = normalize_vehicle(value)
    if not key:
        return r"(?!)"
    return r"^\D*" + r"\D*".join(re.escape(c) for c in key) + r"\D*$"


def get_data_counts() -> dict[str, int]:
    db = get_mongo_db()
    return {
        "customers": db.users.count_documents({}),
        "vehicles": db.vehicledetails.count_documents({}),
        "customer_vehicle_links": db.vehicledetails.count_documents(
            {"customerId": {"$type": "objectId"}}
        ),
        "memberships": db.memberships.count_documents({}),
        "renewal_claims": db.claims.count_documents({}),
        "rc_statuses": db.vehicledetails.count_documents(
            {"rawApiResponse.rcStatus": {"$exists": True, "$nin": [None, ""]}}
        ),
    }


def match_customer_by_mobile(mobile: str) -> str | None:
    phone = normalize_phone(mobile)
    if not phone:
        return None

    db = get_mongo_db()
    matches = []

    for user in db.users.find(
        {"mobileNumber": {"$type": "string"}, "isDeleted": {"$ne": True}},
        {"_id": 1, "mobileNumber": 1},
    ):
        if normalize_phone(user.get("mobileNumber")) == phone:
            matches.append(user["_id"])
            if len(matches) > 1:
                return None

    return str(matches[0]) if len(matches) == 1 else None


def match_customer_identity(name: str, mobile: str) -> str | None:
    target_name = "".join(
        c for c in str(name or "").casefold() if c.isalnum()
    )
    target_phone = normalize_phone(mobile)

    if not target_name or not target_phone:
        return None

    db = get_mongo_db()
    matches = []

    for user in db.users.find(
        {"mobileNumber": {"$type": "string"}, "isDeleted": {"$ne": True}},
        {"_id": 1, "name": 1, "mobileNumber": 1},
    ):
        name_key = "".join(
            c for c in str(user.get("name") or "").casefold() if c.isalnum()
        )
        if (
            name_key == target_name
            and normalize_phone(user.get("mobileNumber")) == target_phone
        ):
            matches.append(user["_id"])
            if len(matches) > 1:
                return None

    return str(matches[0]) if len(matches) == 1 else None


def find_vehicle_number_in_text(text: str) -> str | None:
    pattern = re.compile(
        r"(?<![A-Z0-9])([A-Z]{2}\s*0?\d{1,2}\s*[A-Z]{0,3}\s*\d{1,4}"
        r"|\d{2}\s*BH\s*\d{4}\s*[A-Z]{1,2})(?![A-Z0-9])",
        re.IGNORECASE,
    )

    db = get_mongo_db()
    for match in pattern.finditer(text or ""):
        candidate = match.group(1)
        found = db.vehicledetails.find_one(
            {
                "vehicleNumber": {
                    "$regex": _vehicle_regex(candidate),
                    "$options": "i",
                },
                "isDeleted": {"$ne": True},
            },
            {"vehicleNumber": 1},
        )
        if found:
            return str(found.get("vehicleNumber") or candidate)

    return None


def get_vehicle_snapshot(vehicle_number: str) -> dict[str, Any] | None:
    key = normalize_vehicle(vehicle_number)
    if not key:
        return None

    db = get_mongo_db()
    vehicle = db.vehicledetails.find_one(
        {
            "vehicleNumber": {
                "$regex": _vehicle_regex(vehicle_number),
                "$options": "i",
            },
            "isDeleted": {"$ne": True},
        }
    )
    if not vehicle:
        return None

    raw = vehicle.get("rawApiResponse") or {}
    if not isinstance(raw, dict):
        raw = {}

    def date_text(value):
        if hasattr(value, "date"):
            return value.date().isoformat()
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value).strip() if value else None

    def document(label, value):
        expiry = date_text(value)
        return {
            "document": label,
            "expiry_date": expiry,
            "status": _expiry_status_live(value),
        }

    return {
        "vehicle": {
            "vehicle_number": vehicle.get("vehicleNumber"),
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "financier": raw.get("rcFinancer"),
            "registered_at": vehicle.get("registeredAt"),
            "state": None,
            "insurance_company": vehicle.get("insuranceCompany"),
        },
        "documents": [
            document("Insurance", vehicle.get("insuranceUpto")),
            document("PUC", vehicle.get("pucExpiry")),
            document("Fitness", vehicle.get("fitnessUpto")),
            document("Tax", vehicle.get("taxUpto")),
        ],
    }
