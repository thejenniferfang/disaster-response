"""
Disaster Response System - Entry Point

Run with: python main.py
"""

from src.pipeline import DisasterResponsePipeline
from src.database import DisasterRepository, NGORepository
from src.models import NGO, NGOCapability, DisasterType


def seed_sample_ngos():
    """Seed database with sample NGOs for testing."""
    repo = NGORepository()
    
    sample_ngos = [
        NGO(
            name="Red Cross International",
            description="Global humanitarian organization",
            email="alerts@redcross-test.org",
            contact_name="Emergency Response Team",
            capabilities=[
                NGOCapability.MEDICAL_AID,
                NGOCapability.SEARCH_AND_RESCUE,
                NGOCapability.SHELTER,
                NGOCapability.FOOD_AND_WATER,
            ],
            disaster_types=[dt.value for dt in DisasterType],
            is_global=True,
            active=True,
        ),
        NGO(
            name="Local Relief Foundation",
            description="Regional disaster relief",
            email="help@localrelief-test.org",
            contact_name="Local Coordinator",
            capabilities=[
                NGOCapability.SHELTER,
                NGOCapability.FOOD_AND_WATER,
                NGOCapability.EVACUATION,
            ],
            disaster_types=["flood", "earthquake", "fire"],
            countries=["United States", "Canada"],
            active=True,
        ),
    ]
    
    for ngo in sample_ngos:
        ngo_id = repo.insert(ngo)
        print(f"Added NGO: {ngo.name} (ID: {ngo_id})")


def main():
    """Main entry point."""
    print("=" * 50)
    print("Disaster Response Notification System")
    print("=" * 50)
    
    # Example URLs to monitor (customize these)
    monitoring_urls = [
        # Add actual news/disaster monitoring URLs here
        # "https://example.com/disaster-news",
    ]
    
    # Initialize pipeline
    pipeline = DisasterResponsePipeline()
    
    # Run a full cycle if there are URLs to monitor
    if monitoring_urls:
        summary = pipeline.run_full_cycle(monitoring_urls)
        print(f"\nCycle complete: {summary}")
    else:
        print("\nNo monitoring URLs configured.")
        print("Add URLs to monitoring_urls list or use pipeline methods directly.")
        
        # Process any existing unprocessed disasters
        results = pipeline.process_unprocessed_disasters()
        if results:
            print(f"Processed {len(results)} existing disasters")


if __name__ == "__main__":
    # Uncomment to seed sample NGOs:
    # seed_sample_ngos()
    
    main()
