import os
import sys
from sensor_nc import capture_session, fetch_game_dna
from notary import process_audit
from vault import upload_to_vault

# Configuration
DEEP_DIVE_LIMIT = 5

def start_librarian():
    """
    The Conductor. Orchestrates the Sensor, Notary, and Vault.
    """
    print("=== LIBRARIAN FLEET: CENSUS START ===")
    
    # 1. Room 1: The Sensor
    capture = capture_session()
    if not capture:
        print("!!! Sensor Failed. Aborting Run.")
        sys.exit(1)
        
    run_id = capture['run_id']
    games = capture['games']
    browser = capture['browser']
    
    try:
        # 2. Room 2: The Notary
        registry = process_audit(games, run_id)
        
        # --- DNA Healing Loop ---
        # If we have games with Unknown odds, use the browser we already have open
        healing_count = 0
        for gid, data in registry.items():
            if healing_count >= DEEP_DIVE_LIMIT:
                break
                
            if data["status"] == "ACTIVE" and data.get("overall_odds", "Unknown") == "Unknown":
                print(f"  [Main] DNA Healing: Probing {gid}...")
                new_odds = fetch_game_dna(gid, data['url_slug'], browser)
                if new_odds != "Unknown":
                    data["overall_odds"] = new_odds
                    healing_count += 1
                    print(f"  [Main] DNA Healing Success: {gid} -> {new_odds}")
        
        # Save registry again after potential healing
        import json
        with open("registry.json", 'w') as f:
            json.dump(registry, f, indent=2)

        # 3. Room 3: The Vault
        # Create a temporary copy of registry.json with the run_id for the archive
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
        if os.path.exists(archive_registry):
            os.remove(archive_registry)
            
        if sync_success:
            print(f"=== LIBRARIAN FLEET: RUN {run_id} SUCCESS ===")
        else:
            print(f"=== LIBRARIAN FLEET: RUN {run_id} COMPLETED (Vault Warning) ===")

    finally:
        browser.close()

if __name__ == "__main__":
    start_librarian()
