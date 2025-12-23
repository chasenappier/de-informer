from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class LotteryProvider(ABC):
    """
    Abstract base for state lottery providers.
    Each state implements this interface to enable multi-state scaling.
    """
    
    @property
    @abstractmethod
    def state_code(self) -> str:
        """Two-letter state code (e.g., 'NC', 'TX')"""
        pass
    
    @property
    @abstractmethod
    def target_url(self) -> str:
        """URL of the lottery prizes page"""
        pass
    
    @property
    @abstractmethod
    def safety_threshold(self) -> int:
        """Minimum number of games expected (fail-safe)"""
        pass
    
    @abstractmethod
    def extract_games(self, html_content: str) -> List[Dict]:
        """
        Extract game data from HTML.
        
        Args:
            html_content: Raw HTML from lottery website
            
        Returns:
            List of game dictionaries with keys:
            - game_id: Unique identifier
            - game_name: Display name
            - url_slug: URL fragment for detail page
            - prizes: List of prize tiers
        """
        pass
    
    @abstractmethod
    def fetch_game_details(self, game_id: str, url_slug: str, browser) -> Dict:
        """
        Deep-dive into individual game page for additional metadata.
        
        Args:
            game_id: Game identifier
            url_slug: URL fragment
            browser: Playwright browser instance
            
        Returns:
            Dictionary with additional fields (e.g., overall_odds)
        """
        pass
