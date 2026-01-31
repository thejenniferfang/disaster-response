"""Repository classes for database operations."""

from typing import Optional
from bson import ObjectId
from pymongo.collection import Collection

from src.models import Disaster, NGO, Notification
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
