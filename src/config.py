"""Configuration management - loads from environment variables."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Application configuration."""
    
    # Firecrawl
    firecrawl_api_key: str
    
    # Resend
    resend_api_key: str
    from_email: str
    
    # MongoDB
    mongodb_uri: str
    mongodb_database: str


def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config(
        firecrawl_api_key=os.getenv("FIRECRAWL_API_KEY", ""),
        resend_api_key=os.getenv("RESEND_API_KEY", ""),
        from_email=os.getenv("FROM_EMAIL", "alerts@example.com"),
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_database=os.getenv("MONGODB_DATABASE", "disaster_response"),
    )


# Global config instance
config = load_config()
