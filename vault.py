import os
import boto3
from botocore.config import Config
from datetime import datetime

def upload_to_vault(run_id, html_path, screenshot_path, registry_path="registry.json"):
    """
    Room 3: The Vault.
    Syncs the session package to Cloudflare R2 with standardized naming.
    """
    if not all(os.getenv(v) for v in ['R2_ACCESS_KEY', 'R2_SECRET_KEY', 'R2_ENDPOINT', 'R2_BUCKET']):
        print("[Vault] Skipped: Missing R2 Credentials.")
        return False

    print(f"--- Starting Vault Sync: {run_id} ---")
    
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

    uploads = [
        # (local_path, r2_folder, mime_type)
        (html_path, "raw_html", "text/html"),
        (screenshot_path, "full_screenshot", "image/png"),
        (registry_path, "registry_history", "application/json"),
        ("pulse_history.json", "telemetry_history", "application/json"),
        ("metrics.json", "telemetry_history", "application/json")
    ]

    try:
        for local, folder, mime in uploads:
            if os.path.exists(local):
                # Standardized Name: folder/YYYY/MM/filename
                # For registry_history, we keep the original filename which includes run_id
                r2_key = f"{folder}/{date_path}/{os.path.basename(local)}"
                
                # Special case: The Live Root Mirror (Registry & Telemetry)
                if folder in ["registry_history", "telemetry_history"]:
                    # Also update the root file (e.g., registry.json, pulse_history.json)
                    root_filename = "registry.json" if folder == "registry_history" else local
                    s3.upload_file(local, bucket, root_filename, ExtraArgs={'ContentType': mime})
                    
                    if folder == "registry_history":
                        # The archive name should include the timestamp/run_id properly
                        archive_name = f"registry_{run_id}.json"
                        r2_key = f"registry_history/{date_path}/{archive_name}"
                    elif folder == "telemetry_history":
                        # Archive telemetry with run_id
                        archive_name = f"{os.path.splitext(local)[0]}_{run_id}.json"
                        r2_key = f"{folder}/{date_path}/{archive_name}"

                s3.upload_file(local, bucket, r2_key, ExtraArgs={'ContentType': mime})
                print(f"  [Vault] Uploaded {local} -> {r2_key}")
                
                # Cleanup local evidence files (but keep registry/telemetry for Git/Next Run)
                if local not in [registry_path, "pulse_history.json", "metrics.json"]:
                    os.remove(local)
            else:
                if local not in ["pulse_history.json", "metrics.json"]: # Optional files
                    print(f"  [Vault] Warning: {local} not found.")

        print("[Vault] Sync Complete.")
        return True
    except Exception as e:
        print(f"  [Vault] Sync Failed: {e}")
        return False
