"""
FirecrawlClient - typed wrapper around Firecrawl SDK.

Handles scraping and LLM-based structured extraction.
Site-agnostic: works on any URL without custom parsing.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar, Generic
from pydantic import BaseModel
from firecrawl import FirecrawlApp

from src.config import config


T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ScrapedContent:
    """Raw scraped content from a URL."""
    url: str
    markdown: str
    html: str | None
    metadata: dict[str, Any]
    fetched_at: datetime


@dataclass(frozen=True)
class ExtractionResult(Generic[T]):
    """Result of LLM-based extraction."""
    url: str
    data: T | None
    raw_response: dict[str, Any]
    fetched_at: datetime
    success: bool
    error: str | None = None


class FirecrawlClient:
    """
    Typed client for Firecrawl API.
    
    Provides two main capabilities:
    1. scrape() - Get raw content from any URL
    2. extract() - Use LLM to extract structured data matching a Pydantic schema
    
    The extract() method is site-agnostic: define what you want,
    the LLM figures out where it is on the page.
    """
    
    def __init__(self, api_key: str | None = None):
        """
        Initialize client.
        
        Args:
            api_key: Firecrawl API key. Uses config if not provided.
        """
        self._api_key = api_key or config.firecrawl_api_key
        self._app = FirecrawlApp(api_key=self._api_key)
    
    def scrape(self, url: str, include_html: bool = False) -> ScrapedContent | None:
        """
        Scrape a URL and return raw content.
        
        Args:
            url: The URL to scrape
            include_html: Whether to include raw HTML (default: markdown only)
        
        Returns:
            ScrapedContent or None if scraping failed.
        """
        formats = ["markdown"]
        if include_html:
            formats.append("html")
        
        try:
            result = self._app.scrape_url(url, params={"formats": formats})
            return ScrapedContent(
                url=url,
                markdown=result.get("markdown", ""),
                html=result.get("html") if include_html else None,
                metadata=result.get("metadata", {}),
                fetched_at=datetime.utcnow(),
            )
        except Exception as e:
            print(f"[FirecrawlClient] Scrape failed for {url}: {e}")
            return None
    
    def extract(
        self,
        url: str,
        schema: type[T],
        prompt: str | None = None,
    ) -> ExtractionResult[T]:
        """
        Extract structured data from a URL using LLM.
        
        This is the key method for site-agnostic extraction.
        Define what you want via the schema, the LLM finds it.
        
        Args:
            url: The URL to scrape and extract from
            schema: Pydantic model class defining the structure to extract
            prompt: Optional prompt to guide extraction
        
        Returns:
            ExtractionResult containing the extracted data or error info.
        """
        # Convert Pydantic schema to JSON schema for Firecrawl
        json_schema = schema.model_json_schema()
        
        params: dict[str, Any] = {
            "formats": ["extract"],
            "extract": {"schema": json_schema},
        }
        if prompt:
            params["extract"]["prompt"] = prompt
        
        try:
            result = self._app.scrape_url(url, params=params)
            extracted = result.get("extract")
            
            if extracted:
                # Parse into Pydantic model
                parsed = schema.model_validate(extracted)
                return ExtractionResult(
                    url=url,
                    data=parsed,
                    raw_response=result,
                    fetched_at=datetime.utcnow(),
                    success=True,
                )
            else:
                return ExtractionResult(
                    url=url,
                    data=None,
                    raw_response=result,
                    fetched_at=datetime.utcnow(),
                    success=False,
                    error="No data extracted",
                )
        except Exception as e:
            return ExtractionResult(
                url=url,
                data=None,
                raw_response={},
                fetched_at=datetime.utcnow(),
                success=False,
                error=str(e),
            )
    
    def extract_many(
        self,
        urls: list[str],
        schema: type[T],
        prompt: str | None = None,
    ) -> list[ExtractionResult[T]]:
        """
        Extract from multiple URLs.
        
        Note: This is sequential. For parallel extraction,
        use async or threading at a higher level.
        """
        return [self.extract(url, schema, prompt) for url in urls]
