import os
import json
import boto3
from botocore.config import Config
from datetime import datetime
from differ import (
    compute_data_hash, 
    compute_delta, 
    has_meaningful_changes,
    load_cached_hash,
    save_cached_hash
)


def upload_to_vault(run_id, html_path, screenshot_path, registry_path="registry.json"):
    """
    Room 3: The Vault (Smart Edition).
    
    Syncs the session package to Cloudflare R2 with intelligent deduplication.
    Only archives snapshots when data actually changes, reducing storage by ~75%.
    """
    if not all(os.getenv(v) for v in ['R2_ACCESS_KEY', 'R2_SECRET_KEY', 'R2_ENDPOINT', 'R2_BUCKET']):
        print("[Vault] Skipped: Missing R2 Credentials.")
        return False

    print(f"--- Starting Smart Vault Sync: {run_id} ---")
    
    s3 = boto3.client(
        's3',
        endpoint_url=os.getenv('R2_ENDPOINT'),
        aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('R2_SECRET_KEY'),
        config=Config(signature_version='s3v4')
    )

    bucket = os.getenv('R2_BUCKET')
    now = datetime.now()
    date_path = now.strftime("%Y/%m")
    date_str = now.strftime("%Y-%m-%d")
    
    # === SMART DEDUPLICATION ===
    # Load current registry and compute hash
    with open(registry_path, 'r') as f:
        current_registry = json.load(f)
    
    current_hash = compute_data_hash(current_registry)
    previous_hash = load_cached_hash()
    
    data_changed = (previous_hash != current_hash)
    
    if not data_changed:
        print(f"[Vault] No data changes detected (hash: {current_hash[:8]}...)")
        print("[Vault] Skipping archive upload. Updating live mirrors only.")
    else:
        print(f"[Vault] DATA CHANGED! Old hash: {previous_hash[:8] if previous_hash else 'None'}... -> New hash: {current_hash[:8]}...")
    
    try:
        # === ALWAYS: Update live root mirrors ===
        _upload_live_mirrors(s3, bucket, registry_path)
        
        # === ONLY ON CHANGE: Archive snapshot + Generate delta ===
        if data_changed:
            # Load previous registry for delta computation
            previous_registry = _load_previous_registry(s3, bucket)
            
            if previous_registry:
                delta = compute_delta(previous_registry, current_registry, run_id)
                
                if has_meaningful_changes(delta):
                    # Save and upload delta
                    _upload_delta(s3, bucket, delta, date_path, date_str)
                    
                    # Update rolling changelog
                    _update_changelog(s3, bucket, delta)
                    
                    print(f"[Vault] Delta summary: {delta['summary']}")
            
            # Archive the registry snapshot (only on change)
            archive_name = f"registry_{run_id}.json"
            r2_key = f"registry_history/{date_path}/{archive_name}"
            s3.upload_file(registry_path, bucket, r2_key, ExtraArgs={'ContentType': 'application/json'})
            print(f"  [Vault] Archived snapshot -> {r2_key}")
            
            # Save new hash for next comparison
            save_cached_hash(current_hash)
        
        # === ALWAYS: Upload evidence files ===
        _upload_evidence(s3, bucket, html_path, screenshot_path, date_path)
        
        # === ALWAYS: Upload telemetry ===
        _upload_telemetry(s3, bucket, run_id, date_path)
        
        # Cleanup local evidence files
        for path in [html_path, screenshot_path]:
            if os.path.exists(path):
                os.remove(path)
        
        status = "CHANGED" if data_changed else "UNCHANGED"
        print(f"[Vault] Sync Complete. Status: {status}")
        return True
        
    except Exception as e:
        print(f"  [Vault] Sync Failed: {e}")
        return False


def _upload_live_mirrors(s3, bucket, registry_path):
    """Upload the live versions of registry and telemetry to bucket root."""
    # Live registry
    s3.upload_file(registry_path, bucket, "registry.json", ExtraArgs={'ContentType': 'application/json'})
    print("  [Vault] Updated live mirror -> registry.json")
    
    # Live telemetry
    for telemetry_file in ["pulse_history.json", "metrics.json"]:
        if os.path.exists(telemetry_file):
            s3.upload_file(telemetry_file, bucket, telemetry_file, ExtraArgs={'ContentType': 'application/json'})


def _load_previous_registry(s3, bucket) -> dict:
    """Download the previous registry from R2 for delta comparison."""
    try:
        response = s3.get_object(Bucket=bucket, Key="registry.json")
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"  [Vault] Could not load previous registry: {e}")
        return {}


def _upload_delta(s3, bucket, delta: dict, date_path: str, date_str: str):
    """Upload the delta file to daily_deltas/YYYY/MM/delta_YYYY-MM-DD.json"""
    delta_filename = f"delta_{date_str}.json"
    local_delta_path = f"delta_{date_str}.json"
    
    with open(local_delta_path, 'w') as f:
        json.dump(delta, f, indent=2)
    
    r2_key = f"daily_deltas/{date_path}/{delta_filename}"
    s3.upload_file(local_delta_path, bucket, r2_key, ExtraArgs={'ContentType': 'application/json'})
    print(f"  [Vault] Uploaded delta -> {r2_key}")
    
    # Cleanup local delta file
    os.remove(local_delta_path)


def _update_changelog(s3, bucket, delta: dict):
    """Update the rolling changelog.json at bucket root (last 90 days)."""
    try:
        response = s3.get_object(Bucket=bucket, Key="changelog.json")
        changelog = json.loads(response['Body'].read().decode('utf-8'))
    except:
        changelog = {"schema_version": "1.0", "entries": []}
    
    # Add new entry
    entry = {
        "date": delta["date"],
        "detected_at": delta["detected_at"],
        "run_id": delta["run_id"],
        "wealth_before": delta["wealth_before"],
        "wealth_after": delta["wealth_after"],
        "wealth_delta": delta["wealth_delta"],
        "games_added": len(delta["games_added"]),
        "games_retired": len(delta["games_retired"]),
        "prizes_changed": len(delta["prize_changes"]),
        "summary": delta["summary"],
        "delta_file": f"daily_deltas/{datetime.now().strftime('%Y/%m')}/delta_{delta['date']}.json"
    }
    
    changelog["entries"].insert(0, entry)
    changelog["generated_at"] = datetime.now().isoformat()
    
    # Keep only last 90 days
    changelog["entries"] = changelog["entries"][:90]
    
    # Upload
    local_changelog = "changelog_temp.json"
    with open(local_changelog, 'w') as f:
        json.dump(changelog, f, indent=2)
    
    s3.upload_file(local_changelog, bucket, "changelog.json", ExtraArgs={'ContentType': 'application/json'})
    print("  [Vault] Updated changelog.json")
    
    os.remove(local_changelog)


def _upload_evidence(s3, bucket, html_path, screenshot_path, date_path):
    """Upload raw evidence files (HTML + screenshot)."""
    evidence = [
        (html_path, "raw_html", "text/html"),
        (screenshot_path, "full_screenshot", "image/png"),
    ]
    
    for local, folder, mime in evidence:
        if os.path.exists(local):
            r2_key = f"{folder}/{date_path}/{os.path.basename(local)}"
            s3.upload_file(local, bucket, r2_key, ExtraArgs={'ContentType': mime})
            print(f"  [Vault] Uploaded {local} -> {r2_key}")


def _upload_telemetry(s3, bucket, run_id, date_path):
    """Upload telemetry files to archive."""
    for telemetry_file in ["pulse_history.json", "metrics.json"]:
        if os.path.exists(telemetry_file):
            archive_name = f"{os.path.splitext(telemetry_file)[0]}_{run_id}.json"
            r2_key = f"telemetry_history/{date_path}/{archive_name}"
            s3.upload_file(telemetry_file, bucket, r2_key, ExtraArgs={'ContentType': 'application/json'})

