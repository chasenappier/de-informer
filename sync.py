import os
import json
import boto3 # For R2 (S3-compatible)
from botocore.config import Config

def sync_to_r2():
    """
    Push registry.json and Visual Receipt to Cloudflare R2.
    """
    if not all(os.getenv(v) for v in ['R2_ACCESS_KEY', 'R2_SECRET_KEY', 'R2_ENDPOINT']):
        print("Cloud Sync Skipped: Missing R2 Credentials.")
        return

    s3 = boto3.client(
        's3',
        endpoint_url=os.getenv('R2_ENDPOINT'),
        aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('R2_SECRET_KEY'),
        config=Config(signature_version='s3v4')
    )

    public_url_base = os.getenv('R2_PUBLIC_URL', '').rstrip('/')

    # 1. Upload Registry
    try:
        with open('registry.json', 'rb') as f:
            s3.put_object(
                Bucket=os.getenv('R2_BUCKET'),
                Key='registry.json',
                Body=f,
                ContentType='application/json'
            )
        msg = f" at {public_url_base}/registry.json" if public_url_base else ""
        print(f"Cloud Sync: registry.json pushed to R2{msg}.")
    except Exception as e:
        print(f"Cloud Sync Failed (JSON): {e}")

    # 2. Upload Receipt (Visual Evidence)
    if os.path.exists('.last_receipt'):
        try:
            with open('.last_receipt', 'r') as f:
                receipt_file = f.read().strip()
            
            if os.path.exists(receipt_file):
                with open(receipt_file, 'rb') as f:
                    s3.put_object(
                        Bucket=os.getenv('R2_BUCKET'),
                        Key=f"receipts/{receipt_file}",
                        Body=f,
                        ContentType='image/png'
                    )
                print(f"Cloud Sync: Evidence {receipt_file} vaulted in R2.")
                # Cleanup
                os.remove(receipt_file)
                os.remove('.last_receipt')
        except Exception as e:
            print(f"Cloud Sync Failed (Evidence): {e}")

if __name__ == "__main__":
    print("Starting Cloud Hydration...")
    sync_to_r2()
    # In the future, we add sync_to_postgres() here
