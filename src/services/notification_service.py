"""
Notification Service - sends alerts to NGOs via Resend.

TEAM MEMBER 3: This is your primary file to work on.
Responsible for: Email sending, templates, delivery tracking.
"""

from datetime import datetime
from typing import Optional
import resend

from src.config import config
from src.models import Disaster, NGO, Notification, NotificationStatus
from src.database import NotificationRepository


class NotificationService:
    """Service for sending notifications to NGOs via Resend."""
    
    def __init__(self):
        resend.api_key = config.resend_api_key
        self._from_email = config.from_email
        self._notification_repo = NotificationRepository()
    
    def notify_ngo(self, ngo: NGO, disaster: Disaster) -> Notification:
        """
        Send a notification to an NGO about a disaster.
        
        Args:
            ngo: The NGO to notify
            disaster: The disaster to notify about
        
        Returns:
            Notification record with status.
        """
        # Build email content
        subject = self._build_subject(disaster)
        body = self._build_email_body(ngo, disaster)
        
        # Create notification record
        notification = Notification(
            disaster_id=disaster.id,
            ngo_id=ngo.id,
            to_email=ngo.email,
            subject=subject,
            body=body,
            status=NotificationStatus.PENDING,
        )
        
        # Save to database first
        notification_id = self._notification_repo.insert(notification)
        notification.id = notification_id
        
        # Send via Resend
        try:
            response = resend.Emails.send({
                "from": self._from_email,
                "to": ngo.email,
                "subject": subject,
                "html": body,
            })
            
            # Update status on success
            self._notification_repo.update_status(
                notification_id,
                NotificationStatus.SENT.value,
                resend_id=response.get("id"),
            )
            notification.status = NotificationStatus.SENT
            notification.resend_id = response.get("id")
            notification.sent_at = datetime.utcnow()
            
            print(f"Sent notification to {ngo.name} ({ngo.email})")
            
        except Exception as e:
            # Update status on failure
            error_msg = str(e)
            self._notification_repo.update_status(
                notification_id,
                NotificationStatus.FAILED.value,
                error=error_msg,
            )
            notification.status = NotificationStatus.FAILED
            notification.error_message = error_msg
            
            print(f"Failed to notify {ngo.name}: {error_msg}")
        
        return notification
    
    def notify_ngos_batch(self, ngos: list[NGO], disaster: Disaster) -> list[Notification]:
        """
        Send notifications to multiple NGOs about a disaster.
        
        Args:
            ngos: List of NGOs to notify
            disaster: The disaster to notify about
        
        Returns:
            List of notification records.
        """
        notifications = []
        for ngo in ngos:
            notification = self.notify_ngo(ngo, disaster)
            notifications.append(notification)
        return notifications
    
    def _build_subject(self, disaster: Disaster) -> str:
        """Build email subject line."""
        severity_prefix = {
            "critical": "[URGENT] ",
            "high": "[HIGH PRIORITY] ",
            "medium": "[ALERT] ",
            "low": "[INFO] ",
        }
        
        severity = disaster.severity
        if hasattr(severity, 'value'):
            severity = severity.value
            
        prefix = severity_prefix.get(severity, "[ALERT] ")
        return f"{prefix}{disaster.disaster_type.upper()}: {disaster.title}"
    
    def _build_email_body(self, ngo: NGO, disaster: Disaster) -> str:
        """
        Build email body HTML.
        
        TODO: Expand this with better templates.
        """
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #d32f2f;">Disaster Alert</h1>
            
            <p>Dear {ngo.contact_name or ngo.name} team,</p>
            
            <p>A disaster has been detected that may require your assistance:</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h2 style="margin-top: 0; color: #333;">{disaster.title}</h2>
                <p><strong>Type:</strong> {disaster.disaster_type}</p>
                <p><strong>Severity:</strong> {disaster.severity}</p>
                <p><strong>Location:</strong> {disaster.location}</p>
                {f'<p><strong>Country:</strong> {disaster.country}</p>' if disaster.country else ''}
                <p><strong>Detected:</strong> {disaster.detected_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
            </div>
            
            <h3>Description</h3>
            <p>{disaster.description}</p>
            
            <p><strong>Source:</strong> <a href="{disaster.source_url}">{disaster.source_name or disaster.source_url}</a></p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            
            <p style="color: #666; font-size: 12px;">
                This alert was sent by the Disaster Response Notification System.
                If you believe you received this in error, please contact us.
            </p>
        </body>
        </html>
        """
    
    def get_notification_status(self, notification_id: str) -> Optional[Notification]:
        """Get the current status of a notification."""
        return self._notification_repo.find_by_id(notification_id)
