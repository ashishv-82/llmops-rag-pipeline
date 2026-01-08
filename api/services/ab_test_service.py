"""Service for tracking and analyzing A/B test results for prompt versions."""
from collections import defaultdict
from typing import Dict, List
import json

class ABTestService:
    """Records performance metrics for different prompt versions to enable data-driven selection."""
    
    def __init__(self):
        # In-memory storage for test results
        # In production, this would be backed by Redis or a database
        self.results = defaultdict(lambda: {
            'impressions': 0,
            'total_cost': 0.0,
            'total_tokens': 0,
            'total_latency': 0.0,
            'feedback_scores': []
        })
    
    def record_result(
        self,
        version_id: str,
        cost: float,
        tokens: int,
        latency_ms: float,
        feedback_score: float = None
    ):
        """
        Record A/B test result for a prompt version.
        Tracks cost, latency, and optional user feedback.
        """
        stats = self.results[version_id]
        stats['impressions'] += 1
        stats['total_cost'] += cost
        stats['total_tokens'] += tokens
        stats['total_latency'] += latency_ms
        
        if feedback_score is not None:
            stats['feedback_scores'].append(feedback_score)
    
    def get_report(self, version_ids: List[str]) -> Dict:
        """
        Generate A/B test comparison report.
        Calculates average metrics per version.
        """
        report = {}
        
        for version_id in version_ids:
            stats = self.results[version_id]
            impressions = stats['impressions']
            
            if impressions == 0:
                continue
            
            report[version_id] = {
                'impressions': impressions,
                'avg_cost': stats['total_cost'] / impressions,
                'avg_tokens': stats['total_tokens'] / impressions,
                'avg_latency_ms': stats['total_latency'] / impressions,
                'avg_feedback': (
                    sum(stats['feedback_scores']) / len(stats['feedback_scores'])
                    if stats['feedback_scores'] else None
                )
            }
        
        return report

ab_test_service = ABTestService()