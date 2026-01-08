import sys
import os
import time
import json
from datetime import datetime, timedelta
# Ensure we can import from api
sys.path.append(os.getcwd())

from api.monitoring.drift_detector import drift_detector
from api.monitoring.drift_alerts import check_and_alert_drift

def simulate_drift():
    print("🚀 Starting Data Drift Simulation...")
    
    # 1. Establish Baseline (Short queries)
    # Simulate data from 10 days ago to 3 days ago
    print("\n1️⃣  Generating Baseline Data (Short Queries)...")
    baseline_queries = [
        "reset password", "login failed", "account access", "wifi issue", "email sync",
        "vpn connect", "printer offline", "update driver", "slow laptop", "screen black"
    ]
    
    # We need to hack the timestamps to simulate history
    # Driftdetector uses datetime.now() when recording
    # So we'll manually inject data into the internal storage to simulate history
    
    domain = "support"
    now = datetime.now()
    
    # Simulate 'previous window' (8+ days ago)
    history_start = now - timedelta(days=14)
    
    for i in range(50):
        # Queries from 14 days ago to 8 days ago
        q = baseline_queries[i % len(baseline_queries)]
        ts = history_start + timedelta(hours=i*4) # spread out
        drift_detector.query_data[domain].append((ts, len(q.split())))
        
    print(f"   Stored {len(drift_detector.query_data[domain])} baseline queries.")
    print("   Checking for drift (expecting None/False)...")
    
    # Check drift - should be none as we only have previous window data, no current
    result = drift_detector.detect_drift(domain)
    print(f"   Result: Drift={result.get('drift_detected')}, Reason={result.get('reason', 'N/A')}")
    
    # 2. Simulate Drift (Long, complex queries)
    # Simulate data for 'current window' (last 7 days)
    print("\n2️⃣  Generating Current Data (Long/Complex Queries)...")
    complex_queries = [
        "How do I configure the advanced firewall settings for the new vpn gateway?",
        "What is the procedure for requesting a new software license for the engineering team?",
        "I need to troubleshoot a complex race condition in the production database cluster.",
        "Can you explain the difference between the legacy authentication and the new oauth flow?",
        "My docker container is crashing with an out of memory error during the build process."
    ]
    
    current_start = now - timedelta(days=2)
    
    for i in range(50):
        # Queries from 2 days ago to now
        q = complex_queries[i % len(complex_queries)]
        ts = current_start + timedelta(hours=i)
        drift_detector.query_data[domain].append((ts, len(q.split())))
        
    print(f"   Added {50} complex queries to current window.")
    
    # 3. Detect Drift
    print("\n3️⃣  Detecting Drift...")
    result = check_and_alert_drift(domain, topic_arn=None) # No SNS for test
    
    print(json.dumps(result, indent=2, default=str))
    
    if result.get('drift_detected'):
        print("\n✅ POSITIVE TEST: Drift successfully detected!")
        print(f"   P-Value: {result['p_value']} (< 0.05)")
        print(f"   Mean Length shifted from {result['previous_mean_length']:.1f} to {result['current_mean_length']:.1f}")
    else:
        print("\n❌ NEGATIVE TEST: Drift NOT detected (Unexpected).")

if __name__ == "__main__":
    simulate_drift()
