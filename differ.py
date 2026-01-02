"""
differ.py - The Change Detective

Intelligent change detection for the Smart Inference System.
Computes deterministic hashes and structured deltas for AI analysis.
"""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


def compute_data_hash(registry: dict) -> str:
    """
    Generate a deterministic hash of prize data.
    
    Ignores volatile fields (timestamps, run_ids) to detect actual data changes.
    Only hashes the "DNA" of the data: game_id, prizes, status.
    """
    # Extract only the fields that represent actual data changes
    hashable_data = {}
    
    for game_id, game in registry.items():
        hashable_data[game_id] = {
            "game_id": game.get("game_id"),
            "status": game.get("status"),
            "prizes": game.get("prizes", [])
        }
    
    # Sort keys for deterministic ordering
    serialized = json.dumps(hashable_data, sort_keys=True, cls=DecimalEncoder)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def compute_delta(old_registry: dict, new_registry: dict, run_id: str) -> dict:
    """
    Compute structured delta between two registry states.
    
    Returns an AI-friendly JSON structure describing what changed.
    """
    now = datetime.now()
    
    delta = {
        "date": now.strftime("%Y-%m-%d"),
        "detected_at": now.strftime("%H:%M"),
        "run_id": run_id,
        "games_added": [],
        "games_retired": [],
        "prize_changes": [],
        "wealth_before": 0,
        "wealth_after": 0,
        "wealth_delta": 0,
        "summary": ""
    }
    
    old_ids = set(old_registry.keys())
    new_ids = set(new_registry.keys())
    
    # New games
    for game_id in (new_ids - old_ids):
        game = new_registry[game_id]
        delta["games_added"].append({
            "game_id": game_id,
            "game_name": game.get("game_name", "Unknown"),
            "ticket_price": game.get("ticket_price", "Unknown")
        })
    
    # Retired games
    for game_id in (old_ids - new_ids):
        game = old_registry[game_id]
        delta["games_retired"].append({
            "game_id": game_id,
            "game_name": game.get("game_name", "Unknown")
        })
    
    # Check for status changes (ACTIVE -> RETIRED)
    for game_id in (old_ids & new_ids):
        old_status = old_registry[game_id].get("status")
        new_status = new_registry[game_id].get("status")
        if old_status != new_status:
            delta["games_retired"].append({
                "game_id": game_id,
                "game_name": new_registry[game_id].get("game_name", "Unknown"),
                "reason": f"Status changed: {old_status} -> {new_status}"
            })
    
    # Prize changes (the interesting stuff for AI)
    for game_id in (old_ids & new_ids):
        old_prizes = old_registry[game_id].get("prizes", [])
        new_prizes = new_registry[game_id].get("prizes", [])
        
        # Compare prize totals at each tier
        for i, (old_p, new_p) in enumerate(zip(old_prizes, new_prizes)):
            old_total = int(old_p.get("total", 0))
            new_total = int(new_p.get("total", 0))
            
            if old_total != new_total:
                prize_value = old_p.get("raw_value", old_p.get("value", "?"))
                change = new_total - old_total
                
                delta["prize_changes"].append({
                    "game_id": game_id,
                    "game_name": new_registry[game_id].get("game_name", "Unknown"),
                    "prize_tier": i,
                    "prize_value": str(prize_value),
                    "old_remaining": old_total,
                    "new_remaining": new_total,
                    "change": change,
                    "meaning": f"{abs(change)} {'claimed' if change < 0 else 'added'}"
                })
    
    # Calculate wealth delta
    delta["wealth_before"] = _calculate_total_wealth(old_registry)
    delta["wealth_after"] = _calculate_total_wealth(new_registry)
    delta["wealth_delta"] = delta["wealth_after"] - delta["wealth_before"]
    
    # Generate human-readable summary
    delta["summary"] = _generate_summary(delta)
    
    return delta


def _calculate_total_wealth(registry: dict) -> int:
    """Calculate total remaining prize money across all games."""
    total = 0
    for game in registry.values():
        for prize in game.get("prizes", []):
            try:
                value = int(str(prize.get("value", 0)).replace(",", ""))
                count = int(str(prize.get("total", 0)).replace(",", ""))
                total += value * count
            except (ValueError, TypeError):
                continue
    return total


def _generate_summary(delta: dict) -> str:
    """Generate a human/AI-readable summary of changes."""
    parts = []
    
    if delta["games_added"]:
        names = [g["game_name"] for g in delta["games_added"]]
        parts.append(f"{len(names)} new game(s): {', '.join(names)}")
    
    if delta["games_retired"]:
        names = [g["game_name"] for g in delta["games_retired"]]
        parts.append(f"{len(names)} retired game(s): {', '.join(names)}")
    
    if delta["prize_changes"]:
        # Group by game
        games_with_changes = set(p["game_name"] for p in delta["prize_changes"])
        total_claims = sum(1 for p in delta["prize_changes"] if p["change"] < 0)
        
        # Highlight any top-tier prize claims (first prize tier)
        top_claims = [p for p in delta["prize_changes"] if p["prize_tier"] == 0 and p["change"] < 0]
        
        if top_claims:
            for claim in top_claims:
                parts.append(f"🎰 TOP PRIZE: {claim['prize_value']} claimed in {claim['game_name']}")
        
        if total_claims > len(top_claims):
            parts.append(f"{total_claims - len(top_claims)} other prize(s) claimed across {len(games_with_changes)} game(s)")
    
    if delta["wealth_delta"] != 0:
        direction = "decreased" if delta["wealth_delta"] < 0 else "increased"
        parts.append(f"Total wealth {direction} by ${abs(delta['wealth_delta']):,}")
    
    return "; ".join(parts) if parts else "No significant changes detected"


def has_meaningful_changes(delta: dict) -> bool:
    """Check if the delta contains any actual changes worth storing."""
    return bool(
        delta.get("games_added") or 
        delta.get("games_retired") or 
        delta.get("prize_changes")
    )


def load_cached_hash(cache_path: str = ".last_registry_hash") -> Optional[str]:
    """Load the hash from the last successful run."""
    try:
        with open(cache_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def save_cached_hash(hash_value: str, cache_path: str = ".last_registry_hash"):
    """Save the current hash for future comparison."""
    with open(cache_path, "w") as f:
        f.write(hash_value)
