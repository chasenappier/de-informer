from playwright.sync_api import sync_playwright
import os
import time
import random
import uuid
from datetime import datetime
from bs4 import BeautifulSoup
from user_agents import get_random_user_agent

TARGET_URL = "https://nclottery.com/scratch-off-prizes-remaining"
SAFETY_THRESHOLD = 40

def fetch_game_dna(game_id, url_slug, browser):
    """
    Visit individual game page for Overall Odds.
    """
    url = f"https://nclottery.com/scratch-off/{game_id}/{url_slug}"
    time.sleep(random.uniform(2, 4)) # Jitter
    
    page = browser.new_page(user_agent=get_random_user_agent())
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
        time.sleep(1)
        odds_val = page.query_selector('.odds.value')
        if odds_val:
            val = odds_val.inner_text().replace('1 in ', '').strip()
            page.close()
            return val
    except Exception as e:
        print(f"  [Sensor] Error fetching DNA for {game_id}: {e}")
    page.close()
    return "Unknown"

def capture_session():
    """
    Room 1: The Sensor. 
    Captures raw evidence and extracts the 'Bones' of the registry.
    """
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M')}_{str(uuid.uuid4())[:4]}"
    print(f"--- Starting Sensor Run: {run_id} ---")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a high-quality desktop context for the full screenshot
        context = browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            print(f"[Sensor] Navigating to {TARGET_URL}...")
            page.goto(TARGET_URL, timeout=60000, wait_until="networkidle")
            time.sleep(random.uniform(3, 5)) # Settle jitter
            
            # 1. Capture Raw HTML
            html_content = page.content()
            html_path = f"raw_html_{run_id}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            # 2. Capture Full Screenshot
            screenshot_path = f"screenshot_{run_id}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"[Sensor] Evidence captured: {html_path}, {screenshot_path}")
            
            # 3. Extract Game Data
            soup = BeautifulSoup(html_content, 'html.parser')
            game_boxes = soup.select('div.databox')
            
            if len(game_boxes) < SAFETY_THRESHOLD:
                raise Exception(f"Safety Brake: Only {len(game_boxes)} games found.")

            parsed_games = []
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
                    parsed_games.append({
                        "game_id": game_id,
                        "game_name": game_name,
                        "url_slug": url_slug,
                        "prizes": prizes
                    })
            
            return {
                "run_id": run_id,
                "games": parsed_games,
                "html_path": html_path,
                "html_size_kb": len(html_content) / 1024,
                "screenshot_path": screenshot_path,
                "browser": browser # Handing off browser for DNA deep dives if needed
            }

        except Exception as e:
            print(f"[Sensor] Run Failed: {e}")
            browser.close()
            return None

if __name__ == "__main__":
    # Test run
    data = capture_session()
    if data:
        print(f"Success: Found {len(data['games'])} games.")
        data['browser'].close()
