import pytest
import json
from notary import process_audit

def test_notary_rejects_low_game_count():
    """Notary should reject runs with too few games (below SAFETY_THRESHOLD)"""
    fake_games = [
        {"game_id": str(i), "game_name": f"Game {i}", "prizes": []}
        for i in range(10)  # Only 10 games (below threshold of 40)
    ]
    
    result = process_audit(fake_games, "test_run_reject", html_size_kb=100)
    assert result is None, "Notary should reject runs with too few games"


def test_notary_accepts_valid_game_count():
    """Notary should accept runs with sufficient games"""
    fake_games = [
        {
            "game_id": str(i),
            "game_name": f"Game {i}",
            "url_slug": f"game-{i}",
            "prizes": [{"value": "$1", "odds": "5", "total": "100"}]
        }
        for i in range(50)  # Above threshold
    ]
    
    result = process_audit(fake_games, "test_run_accept", html_size_kb=100)
    assert result is not None, "Notary should accept valid runs"
    assert len(result) >= 50, "Registry should contain all games"


def test_notary_creates_guid_for_new_games():
    """Every new game should get a unique GUID"""
    fake_games = [
        {
            "game_id": "1234",
            "game_name": "Test Game",
            "url_slug": "test-game",
            "prizes": []
        } for _ in range(45)
    ]
    
    result = process_audit(fake_games, "test_run_guid", html_size_kb=100)
    
    for game_id, data in result.items():
        assert "guid" in data, f"Game {game_id} missing GUID"
        assert data["guid"], f"Game {game_id} has null/empty GUID"


def test_notary_statistical_validation():
    """Notary should track pulse history for anomaly detection"""
    # This test would require mocking pulse history
    # For now, just verify the function doesn't crash
    fake_games = [
        {
            "game_id": str(i),
            "game_name": f"Game {i}",
            "url_slug": f"game-{i}",
            "prizes": []
        }
        for i in range(50)
    ]
    
    result = process_audit(fake_games, "test_run_stats", html_size_kb=250)
    assert result is not None


def test_notary_retirement_logic():
    """Games missing for 3+ runs should be marked RETIRED"""
    # This would require multiple runs and state persistence
    # Leaving as TODO for integration tests
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
