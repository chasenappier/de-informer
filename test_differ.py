"""
test_differ.py - Tests for the Smart Inference System

Validates change detection, hash computation, and delta generation.
"""

import pytest
from differ import compute_data_hash, compute_delta, has_meaningful_changes


def test_same_registry_produces_same_hash():
    """Identical data should produce identical hashes."""
    registry = {
        "996": {
            "game_id": "996",
            "status": "ACTIVE",
            "prizes": [{"value": "1000000", "odds": "1469394", "total": 5}]
        }
    }
    
    hash1 = compute_data_hash(registry)
    hash2 = compute_data_hash(registry)
    
    assert hash1 == hash2, "Same registry should produce same hash"


def test_timestamps_ignored_in_hash():
    """Hash should only care about game data, not timestamps."""
    registry1 = {
        "996": {
            "game_id": "996",
            "status": "ACTIVE",
            "prizes": [{"value": "1000000", "total": 5}],
            "last_seen": "2026-01-01T00:00:00",
            "last_run_id": "run_123"
        }
    }
    
    registry2 = {
        "996": {
            "game_id": "996",
            "status": "ACTIVE",
            "prizes": [{"value": "1000000", "total": 5}],
            "last_seen": "2026-01-02T12:00:00",  # Different timestamp
            "last_run_id": "run_456"  # Different run_id
        }
    }
    
    assert compute_data_hash(registry1) == compute_data_hash(registry2), \
        "Timestamps should not affect hash"


def test_prize_change_detected():
    """Changes to prize totals should be detected."""
    old_registry = {
        "996": {
            "game_id": "996",
            "status": "ACTIVE",
            "prizes": [{"value": "1000000", "total": 5}]
        }
    }
    
    new_registry = {
        "996": {
            "game_id": "996",
            "status": "ACTIVE",
            "prizes": [{"value": "1000000", "total": 4}]  # Prize claimed!
        }
    }
    
    hash1 = compute_data_hash(old_registry)
    hash2 = compute_data_hash(new_registry)
    
    assert hash1 != hash2, "Prize change should produce different hash"


def test_delta_detects_prize_change():
    """Delta should capture prize changes with meaning."""
    old_registry = {
        "996": {
            "game_id": "996",
            "game_name": "Million Dollar Game",
            "status": "ACTIVE",
            "prizes": [
                {"value": "1000000", "raw_value": "$1,000,000", "total": 5}
            ]
        }
    }
    
    new_registry = {
        "996": {
            "game_id": "996",
            "game_name": "Million Dollar Game",
            "status": "ACTIVE",
            "prizes": [
                {"value": "1000000", "raw_value": "$1,000,000", "total": 4}
            ]
        }
    }
    
    delta = compute_delta(old_registry, new_registry, "test_run")
    
    assert len(delta["prize_changes"]) == 1
    assert delta["prize_changes"][0]["old_remaining"] == 5
    assert delta["prize_changes"][0]["new_remaining"] == 4
    assert delta["prize_changes"][0]["change"] == -1
    assert "claimed" in delta["prize_changes"][0]["meaning"]


def test_delta_detects_new_game():
    """Delta should capture when a new game appears."""
    old_registry = {}
    new_registry = {
        "999": {
            "game_id": "999",
            "game_name": "New Game",
            "status": "ACTIVE",
            "ticket_price": "$5",
            "prizes": []
        }
    }
    
    delta = compute_delta(old_registry, new_registry, "test_run")
    
    assert len(delta["games_added"]) == 1
    assert delta["games_added"][0]["game_id"] == "999"


def test_no_changes_produces_empty_delta():
    """Identical registries should produce no meaningful changes."""
    registry = {
        "996": {
            "game_id": "996",
            "game_name": "Test Game",
            "status": "ACTIVE",
            "prizes": [{"value": "1000", "total": 10}]
        }
    }
    
    delta = compute_delta(registry, registry, "test_run")
    
    assert not has_meaningful_changes(delta)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
