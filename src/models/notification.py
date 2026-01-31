"""Notification model - tracks notifications sent to NGOs."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NotificationStatus(str, Enum):
    """Status of a notification."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    FAILED = "failed"


class Notification(BaseModel):
    """A notification sent to an NGO about a disaster."""
    
    id: Optional[str] = Field(default=None, description="MongoDB ObjectId as string")
    
    # References
    disaster_id: str
    ngo_id: str
    
    # Email details
    to_email: str
    subject: str
    body: str
    
    # Status tracking
    status: NotificationStatus = NotificationStatus.PENDING
    resend_id: Optional[str] = None  # ID from Resend API
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None

    # Bounce info
    bounce_type: Optional[str] = None

    # Retry tracking
    retry_count: int = 0

    class Config:
        use_enum_values = True
