import json
import os
import uuid
import re
from datetime import datetime

REGISTRY_FILE = "registry.json"
PULSE_FILE = "pulse_history.json"
PULSE_WINDOW = 200 # ~50 days of memory at 4 runs/day

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text).strip('-')
    return text

def calculate_total_wealth(registry):
    """
    Sums up every prize in the registry to calculate the total state wealth.
    Used as an integrity checksum.
    """
    total = 0
    for gid, data in registry.items():
        if data["status"] == "ACTIVE":
            for prize in data.get("prizes", []):
                try:
                    # Convert "$1,000,000" to 1000000
                    val = int(re.sub(r'[^\d]', '', prize['value']))
                    count = int(prize['total'])
                    total += (val * count)
                except (ValueError, KeyError):
                    continue
    return total

def calculate_top_prize_sum(registry):
    """
    Sums up ONLY the value of the remaining #1 top prizes for every game.
    Useful for high-volatility auditing.
    """
    total = 0
    for gid, data in registry.items():
        if data["status"] == "ACTIVE" and data.get("prizes"):
            try:
                # The first prize in the list is usually the top prize
                top_prize = data["prizes"][0]
                val = int(re.sub(r'[^\d]', '', top_prize['value']))
                count = int(top_prize['total'])
                total += (val * count)
            except (ValueError, KeyError, IndexError):
                continue
    return total

def update_pulse(stats):
    """
    Maintains a rolling history of the Librarian's vital signs.
    """
    if os.path.exists(PULSE_FILE):
        with open(PULSE_FILE, 'r') as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    else:
        history = []

    history.append(stats)
    # Keeping the window healthy
    if len(history) > PULSE_WINDOW:
        history = history[-PULSE_WINDOW:]

    with open(PULSE_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    return history

def get_statistical_baseline():
    """
    Calculates the average wealth and game count from memory.
    """
    if not os.path.exists(PULSE_FILE):
        return None
        
    with open(PULSE_FILE, 'r') as f:
        history = json.load(f)
    
    if len(history) < 3: # Need at least a few runs for a baseline
        return None
        
    avg_wealth = sum(h['total_wealth'] for h in history) / len(history)
    avg_games = sum(h['game_count'] for h in history) / len(history)
    
    return {
        "avg_wealth": avg_wealth,
        "avg_games": avg_games,
        "sample_size": len(history)
    }

def process_audit(parsed_games, run_id, html_size_kb=0):
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

    # --- INTEGRITY CHECKSUM (Improvement 1 & Memory) ---
    old_wealth = calculate_total_wealth(registry)
    baseline = get_statistical_baseline()
    
    # Temporarily update registry in memory to check new stats
    temp_registry = registry.copy()
    birth_count = 0
    for game in parsed_games:
        gid = game['game_id']
        if gid not in temp_registry:
            birth_count += 1
        temp_registry[gid] = {"prizes": game["prizes"], "status": "ACTIVE"}

    new_wealth = calculate_total_wealth(temp_registry)
    new_top_prizes = calculate_top_prize_sum(temp_registry)
    new_game_count = len(parsed_games)
    
    # 1. Hard Check (Current vs. Immediately Previous)
    if old_wealth > 0 and new_wealth < (old_wealth * 0.75):
        print(f"!!! [Notary] Hard Integrity Failure: Wealth dropped {((old_wealth-new_wealth)/old_wealth)*100:.1f}%. ABORTING.")
        return None

    # 2. Statistical Check (Current vs. 50-Day Baseline)
    if baseline:
        wealth_diff = abs(new_wealth - baseline['avg_wealth']) / baseline['avg_wealth']
        game_diff = abs(new_game_count - baseline['avg_games']) / baseline['avg_games']
        
        if wealth_diff > 0.40: # 40% deviation from mean is a red flag
            print(f"!!! [Notary] Statistical Anomaly: Wealth differs from {baseline['sample_size']}-run baseline by {wealth_diff*100:.1f}%.")
            # We don't necessarily abort here, but we log it for the Auditor to be aware
    
    # Continue with actual update...
    live_ids = {g['game_id'] for g in parsed_games}
    death_count = 0
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
                death_count += 1
                print(f"  [Notary] Death Event: {gid} ({data['game_name']})")

    # Finalize Pulse Memory
    update_pulse({
        "run_id": run_id,
        "timestamp": now,
        "game_count": new_game_count,
        "total_wealth": new_wealth,
        "top_prize_sum": new_top_prizes,
        "birth_count": birth_count,
        "death_count": death_count,
        "html_size_kb": html_size_kb
    })

    # Save the updated registry
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"[Notary] Audit Complete. Registry holds {len(registry)} total entries.")
    return registry
