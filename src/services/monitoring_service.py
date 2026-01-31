"""
MonitoringService - orchestrates disaster detection across multiple sources.

Uses LLM extraction to pull structured disaster data from any URL.
Site-agnostic: no custom parsers per site.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from src.models import Signal, RawPage
from src.services.firecrawl_client import FirecrawlClient, ExtractionResult
from src.services.extraction_schemas import (
    ExtractedDisasterInfo,
    ExtractedDisasterList,
    SINGLE_DISASTER_PROMPT,
    MULTIPLE_DISASTERS_PROMPT,
)
from src.database.pipeline_mongo import store_raw_page, store_signals


@dataclass
class MonitoringResult:
    """Result of monitoring a single URL."""
    url: str
    success: bool
    raw_page_id: str | None
    signals_created: int
    extraction_time_ms: int
    error: str | None = None


@dataclass
class PollResult:
    """Result of polling multiple URLs."""
    started_at: datetime
    completed_at: datetime
    urls_polled: int
    urls_succeeded: int
    urls_failed: int
    total_signals: int
    results: list[MonitoringResult] = field(default_factory=list)


class MonitoringService:
    """
    Service for monitoring URLs and extracting disaster signals.
    
    Architecture:
    - Uses FirecrawlClient for all scraping/extraction
    - LLM extraction means no site-specific code needed
    - Converts extracted data to Signal objects for the pipeline
    
    Usage:
        service = MonitoringService()
        result = service.poll_urls([
            "https://news-site.com/disasters",
            "https://government-alerts.gov/feed",
        ])
    """
    
    def __init__(
        self,
        client: FirecrawlClient | None = None,
        on_signal_created: Callable[[Signal], None] | None = None,
    ):
        """
        Initialize monitoring service.
        
        Args:
            client: FirecrawlClient instance (creates default if None)
            on_signal_created: Optional callback when a signal is created
        """
        self._client = client or FirecrawlClient()
        self._on_signal_created = on_signal_created
    
    def monitor_url(
        self,
        url: str,
        expect_multiple: bool = False,
    ) -> MonitoringResult:
        """
        Monitor a single URL for disaster information.
        
        Args:
            url: URL to scrape and extract from
            expect_multiple: If True, expects page to list multiple disasters
        
        Returns:
            MonitoringResult with extraction details.
        """
        start_time = datetime.utcnow()
        
        # Choose schema based on expected content type
        if expect_multiple:
            extraction = self._client.extract(
                url,
                ExtractedDisasterList,
                MULTIPLE_DISASTERS_PROMPT,
            )
            disasters = extraction.data.disasters if extraction.data else []
        else:
            extraction = self._client.extract(
                url,
                ExtractedDisasterInfo,
                SINGLE_DISASTER_PROMPT,
            )
            disasters = [extraction.data] if extraction.data and extraction.data.is_confirmed_disaster else []
        
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        if not extraction.success:
            return MonitoringResult(
                url=url,
                success=False,
                raw_page_id=None,
                signals_created=0,
                extraction_time_ms=elapsed_ms,
                error=extraction.error,
            )
        
        # Store raw page
        raw_page_id = store_raw_page(
            url=url,
            content=str(extraction.raw_response),
            source_type="web",
            metadata={"extraction_type": "llm"},
        )
        
        # Convert to signals and store
        signals = self._disasters_to_signals(disasters, raw_page_id)
        if signals:
            store_signals(raw_page_id, signals)
            
            # Fire callbacks
            if self._on_signal_created:
                for sig in signals:
                    self._on_signal_created(sig)
        
        return MonitoringResult(
            url=url,
            success=True,
            raw_page_id=raw_page_id,
            signals_created=len(signals),
            extraction_time_ms=elapsed_ms,
        )
    
    def poll_urls(
        self,
        urls: list[str],
        expect_multiple: bool = False,
    ) -> PollResult:
        """
        Poll multiple URLs for disaster information.
        
        Args:
            urls: List of URLs to monitor
            expect_multiple: If True, expects each page to list multiple disasters
        
        Returns:
            PollResult with aggregated results.
        """
        started_at = datetime.utcnow()
        results: list[MonitoringResult] = []
        
        for url in urls:
            result = self.monitor_url(url, expect_multiple)
            results.append(result)
        
        completed_at = datetime.utcnow()
        
        succeeded = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_signals = sum(r.signals_created for r in results)
        
        return PollResult(
            started_at=started_at,
            completed_at=completed_at,
            urls_polled=len(urls),
            urls_succeeded=succeeded,
            urls_failed=failed,
            total_signals=total_signals,
            results=results,
        )
    
    def _disasters_to_signals(
        self,
        disasters: list[ExtractedDisasterInfo],
        raw_page_id: str,
    ) -> list[dict]:
        """Convert extracted disaster info to signal dicts for storage."""
        signals = []
        
        for disaster in disasters:
            if not disaster.is_confirmed_disaster:
                continue
            
            # Build keywords from available info
            keywords = [disaster.disaster_type, disaster.severity]
            if disaster.country:
                keywords.append(disaster.country)
            if disaster.region:
                keywords.append(disaster.region)
            
            signals.append({
                "raw_page_id": raw_page_id,
                "timestamp": datetime.utcnow(),
                "region": disaster.region or disaster.country or disaster.location,
                "signal_type": disaster.disaster_type,
                "keywords": keywords,
                "source_confidence": 0.7,  # LLM extraction has moderate confidence
                "region_source": "llm",
                "region_confidence": 0.6,
                # Store full extracted data in metadata
                "metadata": {
                    "title": disaster.title,
                    "description": disaster.description,
                    "location": disaster.location,
                    "severity": disaster.severity,
                    "casualties": disaster.casualties,
                    "affected_population": disaster.affected_population,
                    "occurred_at": disaster.occurred_at,
                },
            })
        
        return signals
