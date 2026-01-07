import time
import logging

""" Service for tracking system telemetry and performance metrics """

# Configure application logger for analytics
logger = logging.getLogger("rag-analytics")
logging.basicConfig(level=logging.INFO)


class AnalyticsService:
    # Record query event metadata for observability
    def track_query(self, domain: str, execution_time: float):
        entry = {
            "event": "query_executed",
            "domain": domain,
            "latency_ms": round(execution_time * 1000, 2),
            "timestamp": time.time(),
        }
        logger.info(str(entry))


# Shared instance for tracking
analytics = AnalyticsService()
