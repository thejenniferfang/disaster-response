# Disaster Response Notification System

Monitors online activity for natural disasters/incidents and notifies relevant NGOs.

## Architecture

```
Firecrawl (monitor) → NGO Matcher (find) → Resend (notify)
                           ↓
                       MongoDB (storage)
```

## Project Structure

```
src/
├── models/              # Data models (shared ontology)
│   ├── disaster.py      # Disaster type definitions
│   ├── ngo.py           # NGO type definitions
│   └── notification.py  # Notification tracking
├── services/            # Core business logic
│   ├── firecrawl_service.py   # [TEAM MEMBER 1] Disaster detection
│   ├── ngo_matcher.py         # [TEAM MEMBER 2] NGO matching
│   └── notification_service.py # [TEAM MEMBER 3] Email notifications
├── database/            # MongoDB layer
│   ├── connection.py    # Database connection
│   └── repositories.py  # Data access
├── config.py            # Configuration
└── pipeline.py          # Main workflow orchestrator
```

## Team Member Assignments

1. **Firecrawl Service** (`src/services/firecrawl_service.py`)
   - Web scraping and monitoring
   - Disaster detection and parsing
   - Source management

2. **NGO Matcher** (`src/services/ngo_matcher.py`)
   - Relevance scoring algorithm
   - Geographic matching
   - Capability matching

3. **Notification Service** (`src/services/notification_service.py`)
   - Email templates
   - Delivery tracking
   - Resend API integration

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

3. Start MongoDB (locally or use Atlas)

4. Run:
   ```bash
   python main.py
   ```

## Key Models

- **Disaster**: Detected incident with type, severity, location
- **NGO**: Organization with capabilities and geographic coverage
- **Notification**: Email sent to NGO with tracking

## Usage Example

```python
from src.pipeline import DisasterResponsePipeline

pipeline = DisasterResponsePipeline()

# Monitor specific URLs
disasters = pipeline.run_monitoring([
    "https://news-source.com/disasters",
])

# Process and notify
pipeline.process_unprocessed_disasters()
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `FIRECRAWL_API_KEY` | Firecrawl API key |
| `RESEND_API_KEY` | Resend API key |
| `MONGODB_URI` | MongoDB connection string |
| `MONGODB_DATABASE` | Database name |
| `FROM_EMAIL` | Sender email for notifications |
