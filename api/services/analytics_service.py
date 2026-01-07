"""Service for tracking system telemetry and performance metrics."""

import time
import logging

# Configure application logger for analytics
logger = logging.getLogger("rag-analytics")
logging.basicConfig(level=logging.INFO)


class AnalyticsService:
    """Tracks usage and performance metrics."""

    # pylint: disable=too-few-public-methods

    # Record query event metadata for observability
    def track_query(self, domain: str, execution_time: float):
        """
        Log query execution metrics.
        
        Args:
            domain: The knowledge domain accessed
            execution_time: Time taken to process query in seconds
        """
        entry = {
            "event": "query_executed",
            "domain": domain,
            "latency_ms": round(execution_time * 1000, 2),
            "timestamp": time.time(),
        }
        logger.info(str(entry))


# Shared instance for tracking
analytics = AnalyticsService()
