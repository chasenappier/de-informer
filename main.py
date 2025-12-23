import os
import sys
import time
from opentelemetry import trace
from sensor_nc import capture_session, fetch_game_dna
from notary import process_audit
from vault import upload_to_vault
from logger import setup_logger
from metrics import export_metrics

logger = setup_logger(__name__)

# Configuration
DEEP_DIVE_LIMIT = 5

def start_librarian():
    """
    The Conductor. Orchestrates the Sensor, Notary, and Vault.
    Includes a 3-strike retry loop for stability.
    """
    start_time = time.time()
    logger.info("Census starting", extra={"event": "census_start"})
    
    max_strikes = 3
    for strike in range(1, max_strikes + 1):
        logger.info(f"Retry attempt {strike}/{max_strikes}", extra={"event": "retry_attempt", "strike": strike})
        
        # 1. Room 1: The Sensor
        capture = capture_session()
        if not capture:
            if strike < max_strikes: continue
            else: sys.exit(1)
            
        run_id = capture['run_id']
        games = capture['games']
        html_size = capture.get('html_size_kb', 0)
        
        # 2. Room 2: The Notary (Includes Statistical Audit)
        registry = process_audit(games, run_id, html_size_kb=html_size)
        
        if registry is None:
            logger.warning(f"Audit failed on strike {strike}", extra={"event": "audit_failed", "strike": strike})
            if strike < max_strikes:
                logger.info("Initiating self-repair", extra={"event": "self_repair_start", "delay_seconds": 10})
                time.sleep(10)
                continue
            else:
                logger.error("All attempts exhausted", extra={"event": "census_failed", "strikes": max_strikes})
                sys.exit(1)

        # If we reach here, we have a Verified Truth.
        
        # Note: DNA healing for games with Unknown odds has been moved to notary.py
        # or can be implemented as a separate scheduled maintenance pass
        
        # 3. Room 3: The Vault
        # Create a temporary copy of registry.json with the run_id for the archive
        import json
        archive_registry = f"registry_{run_id}.json"
        with open(archive_registry, 'w') as f:
            json.dump(registry, f, indent=2)
            
        sync_success = upload_to_vault(
            run_id=run_id,
            html_path=capture['html_path'],
            screenshot_path=capture['screenshot_path'],
            registry_path=archive_registry
        )
        
        # Cleanup the temporary archive file
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        
        # Send heartbeat to monitoring service (if configured)
        heartbeat_url = os.getenv('HEARTBEAT_URL')
        if heartbeat_url:
            try:
                import requests
                requests.get(heartbeat_url, timeout=5)
                logger.info("Heartbeat sent", extra={"event": "heartbeat_success"})
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}", extra={"event": "heartbeat_failed", "error": str(e)})
        
        # Export metrics for observability
        export_metrics(run_id, {
            "event": "census_complete",
            "duration_ms": duration_ms,
            "game_count": len(games),
            "html_size_kb": html_size,
            "vault_success": sync_success
        })
        
        if sync_success:
            logger.info("Census completed successfully", extra={
                "event": "census_success",
                "run_id": run_id,
                "duration_ms": duration_ms,
                "game_count": len(games)
            })
            return
        else:
            logger.warning("Census completed with vault warnings", extra={
                "event": "census_partial_success",
                "run_id": run_id,
                "duration_ms": duration_ms
            })
            return



from telemetry import setup_telemetry

# Initialize Telemetry Global
tracer = setup_telemetry("inventory-registry")

if __name__ == "__main__":
    with tracer.start_as_current_span("run_census") as span:
        try:
            start_librarian()
            span.set_status(trace.Status(trace.StatusCode.OK))
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logger.error("Fatal error in main loop", extra={"error": str(e)})
            sys.exit(1)

