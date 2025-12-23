import os

ENV_FILE = ".env"

if os.path.exists(ENV_FILE):
    print(f"--- Keys in {ENV_FILE} ---")
    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            if "=" in line:
                key, val = line.split("=", 1)
                print(f"Found Key: '{key.strip()}' | Length of val: {len(val.strip())}")
else:
    print(".env not found")
