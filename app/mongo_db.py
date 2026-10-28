from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

from .config import BASE_DIR


load_dotenv(BASE_DIR / ".env", override=False)


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    """Create one reusable MongoDB client."""
    uri = os.getenv("MONGODB_URI", "").strip()

    if not uri:
        raise RuntimeError("MONGODB_URI is missing from the .env file.")

    return MongoClient(
        uri,
        serverSelectionTimeoutMS=8000,
        connectTimeoutMS=8000,
        appname="getrightcover-local-chatbot",
    )


def get_mongo_db() -> Database:
    """Return the configured MongoDB database."""
    database = get_mongo_client().get_default_database()

    if database is None:
        raise RuntimeError(
            "MongoDB database name is missing from MONGODB_URI."
        )

    return database
