from playwright.sync_api import sync_playwright
import json
import os
import random
import uuid
import re
import time
from datetime import datetime
from user_agents import get_random_user_agent
from bs4 import BeautifulSoup

TARGET_URL = "https://nclottery.com/scratch-off-prizes-remaining"
REGISTRY_FILE = "registry.json"
SAFETY_THRESHOLD = 40
DEEP_DIVE_LIMIT = 5 # Max new deep dives per run to avoid throttling

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text).strip('-')
    return text

def fetch_game_dna(game_id, url_slug, browser):
    """
    Visit the individual game page to get Overall Odds.
    Only called when missing to keep things fast.
    """
    url = f"https://nclottery.com/scratch-off/{game_id}/{url_slug}"
    # Random wait before deep dive
    time.sleep(random.uniform(2, 5))
    
    page = browser.new_page(user_agent=get_random_user_agent())
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
        # Simulate reading the page
        time.sleep(random.uniform(1, 3))
        
        odds_val = page.query_selector('.odds.value')
        if odds_val:
            val = odds_val.inner_text().replace('1 in ', '').strip()
            page.close()
            return val
    except Exception as e:
        print(f"  Error fetching DNA for {game_id}: {e}")
    page.close()
    return "Unknown"

def fetch_games_with_evidence(playwright):
    """
    Uses Playwright to capture both Data and Visual Evidence.
    """
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(user_agent=get_random_user_agent())
    page = context.new_page()
    
    print(f"Navigating to {TARGET_URL}...")
    try:
        page.goto(TARGET_URL, timeout=60000, wait_until="networkidle")
        # Wait for the databoxes to load
        # Human Jitter: Wait for page to "settle"
        time.sleep(random.uniform(3, 7))
        
        # Capture Visual Evidence (Receipt)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        receipt_path = f"receipt_{timestamp}.png"
        page.screenshot(path=receipt_path, full_page=True)
        
        # --- NEW: Capture Raw HTML Evidence ---
        html_path = f"source_{timestamp}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"  Evidence Captured: {receipt_path} and {html_path}")
        
        # Extract HTML content
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        game_boxes = soup.select('div.databox')
        
        if len(game_boxes) < SAFETY_THRESHOLD:
            print(f"Safety Brake Triggered: Found only {len(game_boxes)} games. Aborting.")
            browser.close()
            return None, None, None

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

            # Extract Static Prize Table
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
                    "ticket_price": "Unknown", # Optional: can extract from class
                    "url_slug": url_slug,
                    "prizes": prizes
                })
        
        return games, receipt_path, html_path, browser
        
    except Exception as e:
        print(f"Error during playwright run: {e}")
        browser.close()
        return None, None, None, None

def update_registry(live_games, browser):
    now = datetime.now().isoformat()
    
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, 'r') as f:
            try:
                registry = json.load(f)
            except json.JSONDecodeError:
                registry = {}
    else:
        registry = {}

    live_ids = {g['game_id'] for g in live_games}
    
    for game in live_games:
        gid = game['game_id']
        p_slug = slugify(game['game_name'])
        
        if gid in registry:
            registry[gid]["last_seen"] = now
            registry[gid]["status"] = "ACTIVE"
            registry[gid]["miss_count"] = 0
            registry[gid]["prizes"] = game["prizes"]
            
            if registry[gid].get("overall_odds", "Unknown") == "Unknown":
                print(f"  Self-Healing: Fetching missing DNA for {gid}...")
                new_odds = fetch_game_dna(gid, game['url_slug'], browser)
                if new_odds != "Unknown":
                    registry[gid]["overall_odds"] = new_odds

            if "guid" not in registry[gid]:
                registry[gid]["guid"] = str(uuid.uuid4())
            if "product_key" not in registry[gid]:
                registry[gid]["product_key"] = p_slug
        else:
            print(f"  New Game: {gid} - {game['game_name']}. Fetching DNA...")
            overall_odds = fetch_game_dna(gid, game['url_slug'], browser)
            
            registry[gid] = {
                "guid": str(uuid.uuid4()),
                "game_id": gid,
                "game_name": game["game_name"],
                "product_key": p_slug,
                "url_slug": game["url_slug"],
                "overall_odds": overall_odds,
                "prizes": game["prizes"],
                "status": "ACTIVE",
                "first_seen": now,
                "last_seen": now,
                "miss_count": 0,
                "death_date": None
            }

    # --- DNA RECOVERY (Improvement 3) ---
    # Look for existing games with "Unknown" DNA and try to heal them
    healing_count = 0
    for gid, data in registry.items():
        if healing_count >= DEEP_DIVE_LIMIT:
            break
            
        if data["status"] == "ACTIVE" and data.get("overall_odds", "Unknown") == "Unknown":
            print(f"  DNA Recovery: Re-probing {gid}...")
            new_odds = fetch_game_dna(gid, data['url_slug'], browser)
            if new_odds != "Unknown":
                data["overall_odds"] = new_odds
                healing_count += 1
                print(f"  DNA Recovery Success: {gid} odds set to {new_odds}")

    # DEATH Management
    for gid, data in registry.items():
        if data["status"] == "ACTIVE" and gid not in live_ids:
            data["miss_count"] += 1
            if data["miss_count"] >= 3:
                data["status"] = "RETIRED"
                data["death_date"] = now
                print(f"  Game {gid} ({data['game_name']}) RETIRED.")

    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Registry updated: {len(live_games)} active games processed.")

if __name__ == "__main__":
    print(f"Starting Census at {datetime.now().isoformat()}...")
    
    with sync_playwright() as p:
        browser_instance = None
        try:
            live_games, receipt_file, html_file, browser_instance = fetch_games_with_evidence(p)
            
            if live_games:
                update_registry(live_games, browser_instance)
                
                # Vault the evidence hand-off for sync.py
                if receipt_file and html_file:
                    with open('.last_evidence', 'w') as f:
                        f.write(f"{receipt_file},{html_file}")
                    print(f"Evidence hand-off created: {receipt_file}, {html_file}")
                
                print("Census complete.")
            else:
                print("Census aborted or failed.")
        finally:
            if browser_instance:
                browser_instance.close()
