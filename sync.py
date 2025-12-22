def sync_to_r2():
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

    now = datetime.now()
    # Organized Path: 2025/12/registry_20251222_1800.json
    folder_path = now.strftime("%Y/%m")
    timestamp = now.strftime("%Y%m%d_%H%M")

    # 1. Upload Registry (Archive + Live)
    try:
        with open('registry.json', 'rb') as f:
            data = f.read()
            # The Timeline Archive
            s3.put_object(Bucket=os.getenv('R2_BUCKET'), 
                         Key=f"timeline/{folder_path}/registry_{timestamp}.json", 
                         Body=data, ContentType='application/json')
            # The Live Mirror
            s3.put_object(Bucket=os.getenv('R2_BUCKET'), Key='registry.json', 
                         Body=data, ContentType='application/json')
        print(f"Cloud Sync: Registry Vaulted in timeline/{folder_path}/")
    except Exception as e:
        print(f"Cloud Sync Failed (JSON): {e}")

    # 2. Upload Evidence (PNG + HTML)
    if os.path.exists('.last_evidence'):
        try:
            with open('.last_evidence', 'r') as f:
                png_file, html_file = f.read().strip().split(',')
            
            for file_path, sub_folder, mime in [(png_file, 'receipts', 'image/png'), 
                                               (html_file, 'raw_source', 'text/html')]:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        s3.put_object(Bucket=os.getenv('R2_BUCKET'),
                                     Key=f"{sub_folder}/{folder_path}/{file_path}",
                                     Body=f, ContentType=mime)
                    os.remove(file_path) # Cleanup factory floor
            
            os.remove('.last_evidence')
            print("Cloud Sync: Visual and Source evidence vaulted.")
        except Exception as e:
            print(f"Cloud Sync Failed (Evidence): {e}")
