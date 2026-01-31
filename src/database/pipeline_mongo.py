"""
Minimal MongoDB helpers for the "raw_pages -> signals -> events" pipeline.

This intentionally avoids extra abstractions so it's easy to explain + demo.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import math
from typing import Any, Iterable, Optional

from bson import ObjectId
from pymongo import DESCENDING, ReturnDocument

from src.database.connection import get_collection


RAW_PAGES = "raw_pages"
SIGNALS = "signals"
EVENTS = "events"


def ensure_pipeline_indexes() -> None:
    """Create the minimal indexes needed for the pipeline collections."""
    raw = get_collection(RAW_PAGES)
    sig = get_collection(SIGNALS)
    evt = get_collection(EVENTS)

    raw.create_index([("url", 1), ("content_hash", 1)], unique=True)
    raw.create_index([("fetched_at", DESCENDING)])
    raw.create_index([("region", 1), ("fetched_at", DESCENDING)])

    sig.create_index([("timestamp", DESCENDING)])
    sig.create_index([("region", 1), ("signal_type", 1), ("timestamp", DESCENDING)])
    sig.create_index([("raw_page_id", 1), ("timestamp", DESCENDING)])

    evt.create_index([("status", 1), ("region", 1), ("event_type", 1)])
    evt.create_index([("first_detected", DESCENDING)])
    evt.create_index([("last_updated", DESCENDING)])


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def store_raw_page(
    *,
    url: str,
    content: str,
    fetched_at: Optional[datetime] = None,
    source_type: Optional[str] = None,
    region: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    content_hash: Optional[str] = None,
) -> str:
    """
    Insert a raw page (ground truth).
    Dedupes by (url, content_hash) and returns the raw_page _id as a string.
    """
    fetched_at = fetched_at or datetime.utcnow()
    metadata = metadata or {}
    content_hash = content_hash or _sha256(content)

    raw = get_collection(RAW_PAGES)
    doc = {
        "url": url,
        "fetched_at": fetched_at,
        "source_type": source_type,
        "region": region,
        "content": content,
        "content_hash": content_hash,
        "metadata": metadata,
    }

    res = raw.find_one_and_update(
        {"url": url, "content_hash": content_hash},
        {"$setOnInsert": doc},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return str(res["_id"])


def store_signals(raw_page_id: str, signals: Iterable[dict[str, Any]]) -> list[str]:
    """
    Insert one or more signals for a raw page.

    Each signal dict should minimally include:
      - region (str)
      - signal_type (str)

    Optional fields:
      - timestamp (datetime; defaults now)
      - keywords (list[str])
      - source_confidence (float)
      - region_source (str)
      - region_confidence (float)
    """
    sig = get_collection(SIGNALS)
    now = datetime.utcnow()

    docs: list[dict[str, Any]] = []
    for s in signals:
        docs.append(
            {
                "raw_page_id": ObjectId(raw_page_id),
                "timestamp": s.get("timestamp") or now,
                "region": s["region"],
                "signal_type": s["signal_type"],
                "keywords": s.get("keywords") or [],
                "source_confidence": float(s.get("source_confidence", 0.5)),
                "region_source": s.get("region_source"),
                "region_confidence": s.get("region_confidence"),
            }
        )

    if not docs:
        return []
    result = sig.insert_many(docs)
    return [str(x) for x in result.inserted_ids]


def detect_event_candidates(
    *,
    window_minutes: int = 30,
    min_count: int = 3,
    max_groups: int = 50,
    max_signal_ids_per_group: int = 25,
) -> list[dict[str, Any]]:
    """
    Group signals by (region, signal_type) in a recent time window.
    Returns candidate dicts used by upsert_event_from_candidate().
    """
    sig = get_collection(SIGNALS)
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": {"region": "$region", "signal_type": "$signal_type"},
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$source_confidence"},
                "signal_ids": {"$push": "$_id"},
                "first_seen": {"$min": "$timestamp"},
                "last_seen": {"$max": "$timestamp"},
            }
        },
        {"$match": {"count": {"$gte": min_count}}},
        {"$sort": {"count": -1, "avg_confidence": -1}},
        {"$limit": max_groups},
    ]

    groups = list(sig.aggregate(pipeline))
    out: list[dict[str, Any]] = []
    for g in groups:
        ids = [str(x) for x in (g.get("signal_ids") or [])][:max_signal_ids_per_group]
        out.append(
            {
                "region": g["_id"]["region"],
                "event_type": g["_id"]["signal_type"],
                "count": int(g.get("count") or 0),
                "avg_confidence": float(g.get("avg_confidence") or 0.0),
                "signal_ids": ids,
                "first_seen": g.get("first_seen"),
                "last_seen": g.get("last_seen"),
            }
        )
    return out


def upsert_event_from_candidate(candidate: dict[str, Any]) -> str:
    """
    Create/update an active event based on a candidate cluster.
    Returns the event _id as a string.
    """
    evt = get_collection(EVENTS)
    now = datetime.utcnow()

    count = int(candidate.get("count") or 0)
    avg_conf = float(candidate.get("avg_confidence") or 0.0)

    strength = 1.0 - math.exp(-count / 5.0)
    confidence = max(0.0, min(1.0, avg_conf * strength))

    region = candidate["region"]
    event_type = candidate["event_type"]
    signal_ids = [ObjectId(x) for x in (candidate.get("signal_ids") or [])]

    res = evt.find_one_and_update(
        {"status": "active", "region": region, "event_type": event_type},
        {
            "$setOnInsert": {
                "status": "active",
                "region": region,
                "event_type": event_type,
                "first_detected": candidate.get("first_seen") or now,
            },
            "$set": {"last_updated": now, "confidence_score": float(confidence)},
            "$addToSet": {"supporting_signals": {"$each": signal_ids}},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return str(res["_id"])

