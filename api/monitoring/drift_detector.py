from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
from scipy.stats import ks_2samp
from typing import Dict, List, Optional

class DriftDetector:
    def __init__(self, window_days: int = 7):
        """
        Initialize DriftDetector.
        
        Args:
            window_days: Number of days to consider for each window (current vs previous).
        """
        self.window_days = window_days
        # Stores list of (timestamp, length) tuples per domain
        # In a real system, this would be backed by a time-series DB or metrics store
        self.query_data: Dict[str, List[tuple]] = defaultdict(list)
    
    def record_query(self, query: str, domain: str = 'general'):
        """
        Record a query's metadata for drift analysis.
        
        Args:
            query: The user query text
            domain: The business domain (e.g., 'legal', 'hr')
        """
        if not query:
            return
            
        timestamp = datetime.now()
        # We track query length (in words) as a simple proxy for complexity/pattern
        length = len(query.split())
        self.query_data[domain].append((timestamp, length))
        
        # Simple cleanup to prevent infinite memory growth in this in-memory implementation
        # Keep last 30 days roughly
        cutoff = datetime.now() - timedelta(days=30)
        self.query_data[domain] = [
            d for d in self.query_data[domain] 
            if d[0] > cutoff
        ]
    
    def detect_drift(self, domain: str = 'general') -> Dict:
        """
        Detect drift in query patterns using Kolmogorov-Smirnov test.
        Compares current window (last 7 days/N days) vs previous window.
        
        Returns:
            Dict containing drift detection results and statistics.
        """
        now = datetime.now()
        current_start = now - timedelta(days=self.window_days)
        previous_start = current_start - timedelta(days=self.window_days)
        
        data = self.query_data.get(domain, [])
        
        # Split data into current and previous windows
        current_window_lengths = [
            length for ts, length in data 
            if ts >= current_start
        ]
        
        previous_window_lengths = [
            length for ts, length in data 
            if previous_start <= ts < current_start
        ]
        
        # Need sufficient data in both windows to be statistically meaningful
        min_samples = 30
        if len(current_window_lengths) < min_samples or len(previous_window_lengths) < min_samples:
            return {
                'drift_detected': False,
                'reason': 'Insufficient data',
                'current_samples': len(current_window_lengths),
                'previous_samples': len(previous_window_lengths)
            }
        
        # Perform Kolmogorov-Smirnov test
        # Null hypothesis: samples are drawn from the same distribution
        statistic, p_value = ks_2samp(current_window_lengths, previous_window_lengths)
        
        # Drift is detected if we reject the null hypothesis (p_value < 0.05)
        is_drift = p_value < 0.05
        
        return {
            'drift_detected': is_drift,
            'p_value': float(p_value),
            'statistic': float(statistic),
            'current_mean_length': float(np.mean(current_window_lengths)),
            'previous_mean_length': float(np.mean(previous_window_lengths)),
            'current_samples': len(current_window_lengths),
            'previous_samples': len(previous_window_lengths)
        }

# Global instance
drift_detector = DriftDetector()
