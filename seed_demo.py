"""
Seed a small, deterministic MongoDB demo dataset for judges.

Run:
  python seed_demo.py

What it does:
  - Inserts a few raw_pages (deduped by url+content_hash)
  - Inserts signals clustered in a region + type (to trigger event detection)
  - Runs the aggregation detector and upserts events
  - Prints active events (with supporting signal ids)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from src.database.connection import close_connection

from src.database.pipeline_mongo import (
    detect_event_candidates,
    ensure_pipeline_indexes,
    store_raw_page,
    store_signals,
    upsert_event_from_candidate,
)


def main() -> None:
    ensure_pipeline_indexes()

    now = datetime.utcnow()

    raw_page_ids: list[str] = []
    raw_page_ids.append(
        store_raw_page(
            url="https://demo.gov.example/sitrep-1",
            fetched_at=now - timedelta(minutes=8),
            source_type="government",
            region="Southern Turkey",
            content=(
                "SITUATION REPORT – EARTHQUAKE\n"
                "Location: Hatay Province, Turkey\n"
                "Power outages reported across Hatay.\n"
                "Hospitals operating on backup generators.\n"
            ),
            metadata={"title": "Situation Report - Earthquake"},
        )
    )
    raw_page_ids.append(
        store_raw_page(
            url="https://demo.news.example/breaking-1",
            fetched_at=now - timedelta(minutes=7),
            source_type="news",
            region="Southern Turkey",
            content=(
                "Breaking: Aftershocks continue near Hatay.\n"
                "Residents report widespread power outages.\n"
            ),
            metadata={"title": "Aftershocks and outages"},
        )
    )
    raw_page_ids.append(
        store_raw_page(
            url="https://demo.ngo.example/update-1",
            fetched_at=now - timedelta(minutes=6),
            source_type="ngo",
            region="Southern Turkey",
            content=(
                "Field update: teams deployed to Hatay.\n"
                "Critical infrastructure outage impacting communications.\n"
            ),
            metadata={"title": "Field update"},
        )
    )

    print(f"Inserted/linked {len(raw_page_ids)} raw_pages.")

    signal_ids: list[str] = []
    signal_ids += store_signals(
        raw_page_ids[0],
        [
            {
                "timestamp": now - timedelta(minutes=8),
                "region": "Hatay Province",
                "signal_type": "infrastructure_outage",
                "keywords": ["power outage", "backup generators"],
                "source_confidence": 0.9,
                "region_source": "heuristic",
                "region_confidence": 0.9,
            }
        ],
    )
    signal_ids += store_signals(
        raw_page_ids[1],
        [
            {
                "timestamp": now - timedelta(minutes=7),
                "region": "Hatay Province",
                "signal_type": "infrastructure_outage",
                "keywords": ["power outages", "aftershocks"],
                "source_confidence": 0.75,
                "region_source": "proximity",
                "region_confidence": 0.75,
            }
        ],
    )
    signal_ids += store_signals(
        raw_page_ids[2],
        [
            {
                "timestamp": now - timedelta(minutes=6),
                "region": "Hatay Province",
                "signal_type": "infrastructure_outage",
                "keywords": ["infrastructure outage", "communications"],
                "source_confidence": 0.8,
                "region_source": "heuristic",
                "region_confidence": 0.85,
            }
        ],
    )

    # Second cluster (smaller) that should NOT trigger if min_count=3
    signal_ids += store_signals(
        raw_page_ids[0],
        [
            {
                "timestamp": now - timedelta(minutes=5),
                "region": "Gaziantep",
                "signal_type": "medical_capacity_strain",
                "keywords": ["hospital", "triage"],
                "source_confidence": 0.65,
                "region_source": "heuristic",
                "region_confidence": 0.7,
            }
        ],
    )
    signal_ids += store_signals(
        raw_page_ids[1],
        [
            {
                "timestamp": now - timedelta(minutes=4),
                "region": "Gaziantep",
                "signal_type": "medical_capacity_strain",
                "keywords": ["injuries", "capacity"],
                "source_confidence": 0.6,
                "region_source": "heuristic",
                "region_confidence": 0.7,
            }
        ],
    )

    print(f"Inserted {len(signal_ids)} signals.")

    candidates = detect_event_candidates(window_minutes=30, min_count=3)
    print(f"Detector found {len(candidates)} event candidate group(s).")

    for c in candidates:
        event_id = upsert_event_from_candidate(c)
        print(f"Upserted event: {event_id} ({c['event_type']} @ {c['region']}, count={c['count']})")

    # Print active events (directly from Mongo, minimal formatting)
    evt = __import__("src.database.connection", fromlist=["get_collection"]).get_collection("events")
    active = list(evt.find({"status": "active"}).sort("last_updated", -1).limit(25))
    print(f"\nActive events: {len(active)}")
    for e in active:
        print(
            f"- {e.get('event_type')} @ {e.get('region')} | confidence={float(e.get('confidence_score') or 0.0):.2f} | "
            f"signals={len(e.get('supporting_signals') or [])}"
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        close_connection()

