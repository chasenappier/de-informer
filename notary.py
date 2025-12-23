import json
import os
import uuid
import re
from datetime import datetime

REGISTRY_FILE = "registry.json"

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text).strip('-')
    return text

def process_audit(parsed_games, run_id):
    """
    Room 2: The Notary.
    Takes raw data and merges it into the Source of Truth (registry.json).
    Assigns GUIDs and manages the Life Cycle (Birth, Stasis, Death).
    """
    print(f"--- Starting Notary Audit: {run_id} ---")
    now = datetime.now().isoformat()
    
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, 'r') as f:
            try:
                registry = json.load(f)
            except json.JSONDecodeError:
                registry = {}
    else:
        registry = {}

    live_ids = {g['game_id'] for g in parsed_games}
    
    for game in parsed_games:
        gid = game['game_id']
        p_slug = slugify(game['game_name'])
        
        if gid in registry:
            # STASIS: Game exists, update its pulse
            registry[gid].update({
                "last_seen": now,
                "status": "ACTIVE",
                "miss_count": 0,
                "prizes": game["prizes"],
                "last_run_id": run_id
            })
        else:
            # BIRTH: New game discovered
            print(f"  [Notary] Birth Event: {gid} - {game['game_name']}")
            registry[gid] = {
                "guid": str(uuid.uuid4()),
                "game_id": gid,
                "game_name": game["game_name"],
                "product_key": p_slug,
                "url_slug": game["url_slug"],
                "overall_odds": "Unknown", # Will be healed by DNA Recovery
                "prizes": game["prizes"],
                "status": "ACTIVE",
                "first_seen": now,
                "last_seen": now,
                "miss_count": 0,
                "death_date": None,
                "last_run_id": run_id
            }

    # DEATH Management
    for gid, data in registry.items():
        if data["status"] == "ACTIVE" and gid not in live_ids:
            data["miss_count"] += 1
            if data["miss_count"] >= 3:
                data["status"] = "RETIRED"
                data["death_date"] = now
                print(f"  [Notary] Death Event: {gid} ({data['game_name']})")

    # Save the updated registry
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"[Notary] Audit Complete. Registry holds {len(registry)} total entries.")
    return registry
