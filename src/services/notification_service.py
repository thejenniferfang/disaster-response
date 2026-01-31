"""
Notification Service - sends alerts to NGOs via Resend.

TEAM MEMBER 3: This is your primary file to work on.
Responsible for: Email sending, templates, delivery tracking.
"""

import logging
import time
from datetime import datetime
from typing import Optional

import resend

from src.config import config
from src.models import Disaster, NGO, Notification, NotificationStatus
from src.database import NotificationRepository
from src.services.template_service import TemplateService

logger = logging.getLogger(__name__)

app_resend = resend(api_key="re_MPbsi958_26tHbygWsVLXT6W9rMmdDqkD")

class NotificationService:
    """Service for sending notifications to NGOs via Resend."""

    # Error types that should be retried
    RETRYABLE_ERRORS = (
        "rate_limit",
        "timeout",
        "connection",
        "temporary",
        "503",
        "502",
        "429",
    )

    def __init__(self, template_service: TemplateService | None = None):
        """
        Initialize the notification service.

        Args:
            template_service: Optional TemplateService instance. Creates one if not provided.
        """
        resend.api_key = config.resend_api_key
        self._from_email = config.from_email
        self._notification_repo = NotificationRepository()
        self._template_service = template_service or TemplateService()
        self._max_retries = config.max_retries
        self._retry_delay = config.retry_delay_seconds

    def notify_ngo(self, ngo: NGO, disaster: Disaster) -> Notification:
        """
        Send a notification to an NGO about a disaster.

        Args:
            ngo: The NGO to notify
            disaster: The disaster to notify about

        Returns:
            Notification record with status.
        """
        # Build email content using templates
        subject = self._build_subject(disaster)
        body = self._template_service.render_disaster_alert(ngo, disaster)

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

        # Send with retry logic
        notification = self._send_with_retry(notification, ngo)

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

    def _send_with_retry(self, notification: Notification, ngo: NGO) -> Notification:
        """
        Send email with exponential backoff retry logic.

        Args:
            notification: The notification to send
            ngo: The NGO being notified (for logging)

        Returns:
            Updated notification with final status.
        """
        last_error = None

        for attempt in range(self._max_retries + 1):
            try:
                response = resend.Emails.send({
                    "from": self._from_email,
                    "to": notification.to_email,
                    "subject": notification.subject,
                    "html": notification.body,
                })

                # Success - update status
                self._notification_repo.update_status(
                    notification.id,
                    NotificationStatus.SENT.value,
                    resend_id=response.get("id"),
                )
                notification.status = NotificationStatus.SENT
                notification.resend_id = response.get("id")
                notification.sent_at = datetime.utcnow()

                logger.info(f"Sent notification to {ngo.name} ({ngo.email})")
                return notification

            except Exception as e:
                last_error = str(e)
                notification.retry_count = attempt + 1

                # Update retry count in database
                self._notification_repo.update_retry_count(notification.id, attempt + 1)

                if self._is_retryable_error(e) and attempt < self._max_retries:
                    # Calculate exponential backoff delay
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Retryable error sending to {ngo.email} (attempt {attempt + 1}/"
                        f"{self._max_retries + 1}): {last_error}. Retrying in {delay}s"
                    )
                    time.sleep(delay)
                else:
                    # Non-retryable or max retries exceeded
                    break

        # All retries failed
        self._notification_repo.update_status(
            notification.id,
            NotificationStatus.FAILED.value,
            error=last_error,
        )
        notification.status = NotificationStatus.FAILED
        notification.error_message = last_error

        logger.error(
            f"Failed to notify {ngo.name} after {notification.retry_count} attempts: {last_error}"
        )

        return notification

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.

        Args:
            error: The exception that occurred

        Returns:
            True if the error is retryable, False otherwise.
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        for retryable in self.RETRYABLE_ERRORS:
            if retryable in error_str or retryable in error_type:
                return True

        return False

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

    def get_notification_status(self, notification_id: str) -> Optional[Notification]:
        """Get the current status of a notification."""
        return self._notification_repo.find_by_id(notification_id)
