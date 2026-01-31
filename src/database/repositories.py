"""Repository classes for database operations."""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Optional
from bson import ObjectId
from pymongo import DESCENDING, ReturnDocument
from pymongo.collection import Collection

from src.models import Disaster, Event, NGO, Notification, RawPage, Signal
from src.database.connection import get_collection


def _to_object_id(id_str: str) -> ObjectId:
    """Convert string ID to ObjectId."""
    return ObjectId(id_str)


def _from_document(doc: dict, model_class: type) -> object:
    """Convert MongoDB document to Pydantic model."""
    if doc is None:
        return None
    doc["id"] = str(doc.pop("_id"))
    return model_class(**doc)


def _to_document(model: object) -> dict:
    """Convert Pydantic model to MongoDB document."""
    doc = model.model_dump(exclude={"id"})
    return doc


def _as_object_ids(ids: list[str]) -> list[ObjectId]:
    return [ObjectId(x) for x in ids]


def _flatten_keywords(nested: list) -> list[str]:
    # Nested can look like [["a","b"], ["b","c"]] depending on aggregation shape.
    out: list[str] = []
    for item in nested:
        if isinstance(item, list):
            for sub in item:
                if isinstance(sub, str):
                    out.append(sub)
        elif isinstance(item, str):
            out.append(item)
    # preserve order-ish but de-dupe
    seen: set[str] = set()
    uniq: list[str] = []
    for kw in out:
        k = kw.strip()
        if not k or k in seen:
            continue
        seen.add(k)
        uniq.append(k)
    return uniq


class DisasterRepository:
    """Repository for Disaster documents."""
    
    def __init__(self):
        self._collection: Collection = get_collection("disasters")
    
    def insert(self, disaster: Disaster) -> str:
        """Insert a disaster and return its ID."""
        doc = _to_document(disaster)
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)
    
    def find_by_id(self, disaster_id: str) -> Optional[Disaster]:
        """Find a disaster by ID."""
        doc = self._collection.find_one({"_id": _to_object_id(disaster_id)})
        return _from_document(doc, Disaster) if doc else None
    
    def find_unprocessed(self) -> list[Disaster]:
        """Find all unprocessed disasters."""
        docs = self._collection.find({"processed": False})
        return [_from_document(doc, Disaster) for doc in docs]
    
    def mark_processed(self, disaster_id: str, ngo_ids: list[str]) -> None:
        """Mark a disaster as processed with notified NGOs."""
        self._collection.update_one(
            {"_id": _to_object_id(disaster_id)},
            {"$set": {"processed": True, "ngos_notified": ngo_ids}}
        )
    
    def find_recent(self, limit: int = 10) -> list[Disaster]:
        """Find recent disasters."""
        docs = self._collection.find().sort("detected_at", -1).limit(limit)
        return [_from_document(doc, Disaster) for doc in docs]


class NGORepository:
    """Repository for NGO documents."""
    
    def __init__(self):
        self._collection: Collection = get_collection("ngos")
    
    def insert(self, ngo: NGO) -> str:
        """Insert an NGO and return its ID."""
        doc = _to_document(ngo)
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)
    
    def find_by_id(self, ngo_id: str) -> Optional[NGO]:
        """Find an NGO by ID."""
        doc = self._collection.find_one({"_id": _to_object_id(ngo_id)})
        return _from_document(doc, NGO) if doc else None
    
    def find_all_active(self) -> list[NGO]:
        """Find all active NGOs."""
        docs = self._collection.find({"active": True})
        return [_from_document(doc, NGO) for doc in docs]
    
    def find_by_capability(self, capability: str) -> list[NGO]:
        """Find NGOs with a specific capability."""
        docs = self._collection.find({"capabilities": capability, "active": True})
        return [_from_document(doc, NGO) for doc in docs]
    
    def find_by_country(self, country: str) -> list[NGO]:
        """Find NGOs operating in a country."""
        docs = self._collection.find({
            "$or": [
                {"countries": country},
                {"is_global": True}
            ],
            "active": True
        })
        return [_from_document(doc, NGO) for doc in docs]


class NotificationRepository:
    """Repository for Notification documents."""
    
    def __init__(self):
        self._collection: Collection = get_collection("notifications")
    
    def insert(self, notification: Notification) -> str:
        """Insert a notification and return its ID."""
        doc = _to_document(notification)
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)
    
    def find_by_id(self, notification_id: str) -> Optional[Notification]:
        """Find a notification by ID."""
        doc = self._collection.find_one({"_id": _to_object_id(notification_id)})
        return _from_document(doc, Notification) if doc else None
    
    def find_by_disaster(self, disaster_id: str) -> list[Notification]:
        """Find all notifications for a disaster."""
        docs = self._collection.find({"disaster_id": disaster_id})
        return [_from_document(doc, Notification) for doc in docs]
    
    def update_status(self, notification_id: str, status: str, 
                      resend_id: Optional[str] = None, 
                      error: Optional[str] = None) -> None:
        """Update notification status."""
        update = {"$set": {"status": status}}
        if resend_id:
            update["$set"]["resend_id"] = resend_id
        if error:
            update["$set"]["error_message"] = error
        self._collection.update_one(
            {"_id": _to_object_id(notification_id)},
            update
        )


# ----------------------------
# Pipeline collections (judge-friendly lineage):
# raw_pages -> signals -> events
# ----------------------------


class RawPageRepository:
    """Repository for RawPage documents (ground truth)."""

    def __init__(self):
        self._collection: Collection = get_collection("raw_pages")
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index([("url", 1), ("content_hash", 1)], unique=True)
        self._collection.create_index([("fetched_at", DESCENDING)])
        self._collection.create_index([("region", 1), ("fetched_at", DESCENDING)])

    def insert_or_get(self, raw_page: RawPage) -> str:
        """
        Insert raw page if (url, content_hash) is new; otherwise return existing id.
        """
        doc = _to_document(raw_page)
        res = self._collection.find_one_and_update(
            {"url": raw_page.url, "content_hash": raw_page.content_hash},
            {"$setOnInsert": doc},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return str(res["_id"])

    def find_by_id(self, raw_page_id: str) -> Optional[RawPage]:
        doc = self._collection.find_one({"_id": _to_object_id(raw_page_id)})
        return _from_document(doc, RawPage) if doc else None


class SignalRepository:
    """Repository for Signal documents (core abstraction)."""

    def __init__(self):
        self._collection: Collection = get_collection("signals")
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index([("timestamp", DESCENDING)])
        self._collection.create_index([("region", 1), ("signal_type", 1), ("timestamp", DESCENDING)])
        self._collection.create_index([("raw_page_id", 1), ("timestamp", DESCENDING)])

    def insert(self, signal: Signal) -> str:
        doc = _to_document(signal)
        # Store raw_page_id as ObjectId in Mongo for joins/traceability.
        doc["raw_page_id"] = _to_object_id(signal.raw_page_id)
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)

    def insert_many(self, signals: list[Signal]) -> list[str]:
        if not signals:
            return []
        docs: list[dict] = []
        for s in signals:
            d = _to_document(s)
            d["raw_page_id"] = _to_object_id(s.raw_page_id)
            docs.append(d)
        result = self._collection.insert_many(docs)
        return [str(x) for x in result.inserted_ids]

    def find_recent(self, minutes: int = 30, limit: int = 200) -> list[Signal]:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        docs = (
            self._collection.find({"timestamp": {"$gte": cutoff}})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        out: list[Signal] = []
        for doc in docs:
            # Normalize raw_page_id back to string for model
            if "raw_page_id" in doc and isinstance(doc["raw_page_id"], ObjectId):
                doc["raw_page_id"] = str(doc["raw_page_id"])
            out.append(_from_document(doc, Signal))
        return out

    def aggregate_event_candidates(
        self,
        window_minutes: int = 30,
        min_count: int = 3,
        max_groups: int = 50,
        max_signal_ids_per_group: int = 25,
    ) -> list[dict]:
        """
        Detect emerging clusters: group by (region, signal_type) over a time window.
        Returns dicts with: region, event_type, count, avg_confidence, keywords, signal_ids, first_seen, last_seen.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {
                "$group": {
                    "_id": {"region": "$region", "signal_type": "$signal_type"},
                    "count": {"$sum": 1},
                    "avg_confidence": {"$avg": "$source_confidence"},
                    "signal_ids": {"$push": "$_id"},
                    "keywords": {"$addToSet": "$keywords"},
                    "first_seen": {"$min": "$timestamp"},
                    "last_seen": {"$max": "$timestamp"},
                }
            },
            {"$match": {"count": {"$gte": min_count}}},
            {"$sort": {"count": -1, "avg_confidence": -1}},
            {"$limit": max_groups},
        ]
        groups = list(self._collection.aggregate(pipeline))
        out: list[dict] = []
        for g in groups:
            region = g["_id"]["region"]
            event_type = g["_id"]["signal_type"]  # simplest mapping
            signal_ids = [str(x) for x in (g.get("signal_ids") or [])][:max_signal_ids_per_group]
            keywords = _flatten_keywords(g.get("keywords") or [])
            out.append(
                {
                    "region": region,
                    "event_type": event_type,
                    "count": int(g.get("count") or 0),
                    "avg_confidence": float(g.get("avg_confidence") or 0.0),
                    "keywords": keywords,
                    "signal_ids": signal_ids,
                    "first_seen": g.get("first_seen"),
                    "last_seen": g.get("last_seen"),
                }
            )
        return out


class EventRepository:
    """Repository for Event documents (derived from signals)."""

    def __init__(self):
        self._collection: Collection = get_collection("events")
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index([("status", 1), ("region", 1), ("event_type", 1)])
        self._collection.create_index([("first_detected", DESCENDING)])
        self._collection.create_index([("last_updated", DESCENDING)])

    def upsert_active_event_from_candidate(self, candidate: dict) -> str:
        """
        Create/update an active event given an aggregation candidate from signals.
        """
        now = datetime.utcnow()
        count = int(candidate.get("count") or 0)
        avg_conf = float(candidate.get("avg_confidence") or 0.0)

        # Simple, explainable confidence curve (bounded [0,1]).
        # Strength grows with count; avg_conf weights it.
        strength = 1.0 - math.exp(-count / 5.0)  # ~0.18 @1, ~0.45 @3, ~0.63 @5, ~0.86 @10
        confidence = max(0.0, min(1.0, avg_conf * strength))

        region = candidate["region"]
        event_type = candidate["event_type"]
        signal_ids = candidate.get("signal_ids") or []

        res = self._collection.find_one_and_update(
            {"status": "active", "region": region, "event_type": event_type},
            {
                "$setOnInsert": {
                    "status": "active",
                    "region": region,
                    "event_type": event_type,
                    "first_detected": candidate.get("first_seen") or now,
                },
                "$set": {
                    "last_updated": now,
                    "confidence_score": float(confidence),
                },
                "$addToSet": {"supporting_signals": {"$each": _as_object_ids(signal_ids)}},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return str(res["_id"])

    def find_active(self, limit: int = 25) -> list[Event]:
        docs = (
            self._collection.find({"status": "active"})
            .sort("last_updated", DESCENDING)
            .limit(limit)
        )
        out: list[Event] = []
        for doc in docs:
            # supporting_signals stored as ObjectId in Mongo; expose as strings in model
            if "supporting_signals" in doc:
                doc["supporting_signals"] = [str(x) for x in doc.get("supporting_signals") or []]
            out.append(_from_document(doc, Event))
        return out

