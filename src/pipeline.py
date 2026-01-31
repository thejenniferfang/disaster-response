"""
Main Pipeline - orchestrates the disaster response workflow.

Flow: Firecrawl (detect) -> NGO Matcher (find) -> Notification (send)
"""

from src.models import Disaster
from src.services import FirecrawlService, NGOMatcher, NotificationService
from src.database import DisasterRepository


class DisasterResponsePipeline:
    """
    Main pipeline that orchestrates the disaster response workflow.
    
    1. Monitor sources for disasters (Firecrawl)
    2. Find relevant NGOs for each disaster (Matcher)
    3. Send notifications to NGOs (Resend)
    """
    
    def __init__(self):
        self.firecrawl = FirecrawlService()
        self.matcher = NGOMatcher()
        self.notifier = NotificationService()
        self._disaster_repo = DisasterRepository()
    
    def run_monitoring(self, urls: list[str]) -> list[Disaster]:
        """
        Run the monitoring phase - detect new disasters.
        
        Args:
            urls: List of URLs to monitor for disasters
        
        Returns:
            List of newly detected disasters.
        """
        print("=== Starting disaster monitoring ===")
        disasters = self.firecrawl.monitor_sources(urls)
        print(f"Detected {len(disasters)} new disasters")
        return disasters
    
    def process_disaster(self, disaster: Disaster, max_ngos: int = 10) -> dict:
        """
        Process a single disaster - find NGOs and send notifications.
        
        Args:
            disaster: The disaster to process
            max_ngos: Maximum number of NGOs to notify
        
        Returns:
            Summary dict with results.
        """
        print(f"=== Processing disaster: {disaster.title} ===")
        
        # Find relevant NGOs
        ngos = self.matcher.get_top_ngos(disaster, limit=max_ngos)
        print(f"Found {len(ngos)} relevant NGOs")
        
        if not ngos:
            print("No relevant NGOs found")
            return {
                "disaster": disaster,
                "ngos_found": 0,
                "notifications_sent": 0,
                "notifications_failed": 0,
            }
        
        # Send notifications
        notifications = self.notifier.notify_ngos_batch(ngos, disaster)
        
        # Mark disaster as processed
        ngo_ids = [ngo.id for ngo in ngos if ngo.id]
        if disaster.id:
            self._disaster_repo.mark_processed(disaster.id, ngo_ids)
        
        # Count results
        sent = sum(1 for n in notifications if n.status == "sent")
        failed = sum(1 for n in notifications if n.status == "failed")
        
        print(f"Sent: {sent}, Failed: {failed}")
        
        return {
            "disaster": disaster,
            "ngos_found": len(ngos),
            "notifications_sent": sent,
            "notifications_failed": failed,
        }
    
    def process_unprocessed_disasters(self, max_ngos: int = 10) -> list[dict]:
        """
        Process all unprocessed disasters in the database.
        
        Returns:
            List of processing summaries.
        """
        disasters = self._disaster_repo.find_unprocessed()
        print(f"Found {len(disasters)} unprocessed disasters")
        
        results = []
        for disaster in disasters:
            result = self.process_disaster(disaster, max_ngos)
            results.append(result)
        
        return results
    
    def run_full_cycle(self, urls: list[str], max_ngos: int = 10) -> dict:
        """
        Run a full monitoring and processing cycle.
        
        Args:
            urls: URLs to monitor
            max_ngos: Max NGOs to notify per disaster
        
        Returns:
            Summary of the cycle.
        """
        # Phase 1: Monitor for new disasters
        new_disasters = self.run_monitoring(urls)
        
        # Phase 2: Process all unprocessed disasters
        results = self.process_unprocessed_disasters(max_ngos)
        
        return {
            "new_disasters_detected": len(new_disasters),
            "disasters_processed": len(results),
            "results": results,
        }
