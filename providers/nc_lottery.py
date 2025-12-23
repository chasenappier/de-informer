import time
import random
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from providers.base import LotteryProvider
from user_agents import get_random_user_agent

class NorthCarolinaProvider(LotteryProvider):
    """North Carolina Lottery Provider"""
    
    @property
    def state_code(self) -> str:
        return "NC"
    
    @property
    def target_url(self) -> str:
        return "https://nclottery.com/scratch-off-prizes-remaining"
    
    @property
    def safety_threshold(self) -> int:
        return 40
    
    def extract_games(self, html_content: str) -> List[Dict]:
        """Extract games from NC Lottery HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        game_boxes = soup.select('div.databox')
        
        if len(game_boxes) < self.safety_threshold:
            raise Exception(f"Safety Brake: Only {len(game_boxes)} games found (threshold: {self.safety_threshold})")
        
        games = []
        for box in game_boxes:
            id_span = box.select_one('span.gamenumber')
            game_id = "".join(filter(str.isdigit, id_span.get_text())) if id_span else None
            
            name_link = box.select_one('span.gamename a')
            game_name = name_link.get_text(strip=True) if name_link else "Unknown"
            
            url_slug = "unknown"
            if name_link and 'href' in name_link.attrs:
                parts = name_link['href'].strip('/').split('/')
                if len(parts) >= 3:
                    url_slug = parts[2]
            
            prizes = []
            table = box.select_one('table.datatable')
            if table:
                rows = table.select('tbody tr')
                for row in rows:
                    cols = row.select('td')
                    if len(cols) >= 4:
                        prizes.append({
                            "value": cols[0].get_text(strip=True),
                            "odds": cols[1].get_text(strip=True).replace('1 in ', ''),
                            "total": cols[2].get_text(strip=True).replace(',', '')
                        })
            
            if game_id:
                games.append({
                    "game_id": game_id,
                    "game_name": game_name,
                    "url_slug": url_slug,
                    "prizes": prizes
                })
        
        return games
    
    def fetch_game_details(self, game_id: str, url_slug: str, browser) -> Dict:
        """Fetch overall odds from game detail page"""
        url = f"https://nclottery.com/scratch-off/{game_id}/{url_slug}"
        time.sleep(random.uniform(2, 4))  # Human-like jitter
        
        page = browser.new_page(user_agent=get_random_user_agent())
        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
            time.sleep(1)
            odds_val = page.query_selector('.odds.value')
            if odds_val:
                val = odds_val.inner_text().replace('1 in ', '').strip()
                page.close()
                return {"overall_odds": val}
        except Exception as e:
            print(f"  [Provider:NC] Error fetching details for {game_id}: {e}")
        finally:
            page.close()
        
        return {"overall_odds": "Unknown"}

# Auto-register
from providers import register_provider
register_provider("NC", NorthCarolinaProvider())
