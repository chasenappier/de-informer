import os
import boto3
from botocore.config import Config

ENV_FILE = ".env"

def load_env():
    """Manually load .env file"""
    if os.path.exists(ENV_FILE):
        print(f"📄 Loading {ENV_FILE}...")
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Handle 'export ' prefix
                if line.lower().startswith("export "):
                    line = line[7:].strip()
                    
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ[key] = val
    else:
        print(f"⚠️ {ENV_FILE} not found!")

def fix_cors():
    load_env()
    
    endpoint = os.getenv('R2_ENDPOINT')
    
    # Try multiple variations of key names
    key_id = os.getenv('R2_ACCESS_KEY') or os.getenv('R2_ACCESS_KEY_ID')
    secret = os.getenv('R2_SECRET_KEY') or os.getenv('R2_SECRET_ACCESS_KEY')
    bucket = os.getenv('R2_BUCKET') or os.getenv('R2_BUCKET_NAME')
    
    missing = []
    if not endpoint: missing.append("R2_ENDPOINT")
    if not key_id: missing.append("R2_ACCESS_KEY / R2_ACCESS_KEY_ID")
    if not secret: missing.append("R2_SECRET_KEY / R2_SECRET_ACCESS_KEY")
    if not bucket: missing.append("R2_BUCKET / R2_BUCKET_NAME")

    if missing:
        print(f"❌ Missing credentials in .env: {', '.join(missing)}")
        return

    print(f"🔧 Applying CORS to bucket: {bucket}...")
    
    s3 = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        config=Config(signature_version='s3v4')
    )

    cors_configuration = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'HEAD'],
            'AllowedOrigins': ['*'], # Allow Mission Control to access data
            'ExposeHeaders': []
        }]
    }

    try:
        s3.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_configuration)
        print("✅ CORS Policy Updated Successfully!")
        print("   Allowed Origins: *")
        print("   Allowed Methods: GET, HEAD")
        print("   --> Your dashboard should work now (refresh in 30s).")
    except Exception as e:
        print(f"❌ Failed to set CORS: {e}")

if __name__ == "__main__":
    fix_cors()
