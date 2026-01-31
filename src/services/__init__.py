"""Services - core business logic."""

from src.services.firecrawl_client import FirecrawlClient, ScrapedContent, ExtractionResult
from src.services.extraction_schemas import (
    ExtractedDisasterInfo,
    ExtractedDisasterList,
    SINGLE_DISASTER_PROMPT,
    MULTIPLE_DISASTERS_PROMPT,
)
from src.services.monitoring_service import MonitoringService, MonitoringResult, PollResult
from src.services.ngo_matcher import NGOMatcher
from src.services.notification_service import NotificationService
from src.services.template_service import TemplateService

__all__ = [
    # Firecrawl
    "FirecrawlClient",
    "ScrapedContent",
    "ExtractionResult",
    # Extraction schemas
    "ExtractedDisasterInfo",
    "ExtractedDisasterList",
    "SINGLE_DISASTER_PROMPT",
    "MULTIPLE_DISASTERS_PROMPT",
    # Monitoring
    "MonitoringService",
    "MonitoringResult",
    "PollResult",
    # NGO & Notifications
    "NGOMatcher",
    "NotificationService",
    "TemplateService",
]
