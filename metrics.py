# Metrics Export Module
# Exports run metrics for Grafana/observability dashboards

import json
import os
from datetime import datetime
from typing import Dict, Any

METRICS_FILE = "metrics.json"

def export_metrics(run_id: str, metrics: Dict[str, Any]):
    """
    Export metrics to JSON file for consumption by monitoring tools.
    
    Args:
        run_id: Unique run identifier
        metrics: Dictionary of metric values
    """
    metric_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "run_id": run_id,
        **metrics
    }
    
    # Append to metrics file (create if doesn feed exists)
    existing_metrics = []
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, 'r') as f:
            try:
                existing_metrics = json.load(f)
            except json.JSONDecodeError:
                existing_metrics = []
    
    existing_metrics.append(metric_entry)
    
    # Keep last 200 entries (approx 50 days at 4x/day)
    if len(existing_metrics) > 200:
        existing_metrics = existing_metrics[-200:]
    
    with open(METRICS_FILE, 'w') as f:
        json.dump(existing_metrics, f, indent=2)


def get_latest_metrics(count: int = 10) -> list:
    """Get the N most recent metric entries"""
    if not os.path.exists(METRICS_FILE):
        return []
    
    with open(METRICS_FILE, 'r') as f:
        try:
            metrics = json.load(f)
            return metrics[-count:]
        except json.JSONDecodeError:
            return []
