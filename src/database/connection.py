"""MongoDB connection management."""

from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from src.config import config

# Module-level client (lazy initialized)
_client: Optional[MongoClient] = None


def get_client() -> MongoClient:
    """Get or create the MongoDB client."""
    global _client
    if _client is None:
        _client = MongoClient(config.mongodb_uri)
    return _client


def get_database() -> Database:
    """Get the application database."""
    return get_client()[config.mongodb_database]


def get_collection(name: str) -> Collection:
    """Get a collection by name."""
    return get_database()[name]


def close_connection() -> None:
    """Close the MongoDB connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
