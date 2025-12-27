from playwright.sync_api import sync_playwright
import os
import time
import random
import uuid
from datetime import datetime
from bs4 import BeautifulSoup
from pydantic import ValidationError
from user_agents import get_random_user_agent
from logger import setup_logger
from opentelemetry import trace
from models import validate_extracted_game, GameRaw, SensorOutput

logger = setup_logger(__name__)
tracer = trace.get_tracer(__name__)

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
    logger.info("Sensor run starting", extra={"event": "sensor_start", "run_id": run_id})
    
    with tracer.start_as_current_span("sensor_capture") as span:
        span.set_attribute("run_id", run_id)
        span.set_attribute("target_url", TARGET_URL)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Use a high-quality desktop context for the full screenshot
            context = browser.new_context(
                user_agent=get_random_user_agent(),
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            try:
                logger.info("Navigating to target", extra={"event": "navigation_start", "url": TARGET_URL, "run_id": run_id})
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
                
                html_size = round(len(html_content) / 1024, 2)
                span.set_attribute("html_size_kb", html_size)
                
                logger.info("Evidence captured", extra={
                    "event": "evidence_captured",
                    "run_id": run_id,
                    "html_path": html_path,
                    "screenshot_path": screenshot_path,
                    "html_size_kb": html_size
                })
                
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
                                    "odds": cols[1].get_text(strip=True),
                                    "total": cols[2].get_text(strip=True)
                                })
                    
                    if game_id and prizes:
                        try:
                            # PYDANTIC FORTRESS: Validate EVERY game at extraction
                            validated_game = validate_extracted_game(
                                game_id=game_id,
                                game_name=game_name,
                                url_slug=url_slug,
                                prizes=prizes
                            )
                            parsed_games.append(validated_game)
                        except ValidationError as ve:
                            # Log validation failure but continue with other games
                            logger.warning(f"Game {game_id} failed validation: {ve.error_count()} errors", 
                                extra={"event": "validation_failed", "game_id": game_id, "errors": str(ve)})
                
                span.set_attribute("games_found", len(parsed_games))
                
                # FINAL VALIDATION: Wrap entire output in SensorOutput model
                try:
                    validated_output = SensorOutput(
                        run_id=run_id,
                        games=parsed_games,
                        html_path=html_path,
                        html_size_kb=len(html_content) / 1024,
                        screenshot_path=screenshot_path
                    )
                    
                    logger.info("Sensor validation complete", extra={
                        "event": "validation_success",
                        "run_id": run_id,
                        "games_validated": validated_output.total_games(),
                        "universe_value": str(validated_output.total_universe_value())
                    })
                    
                    # Return as dict for backwards compatibility with notary.py
                    # Use mode='json' to convert Decimals to JSON-serializable types
                    return {
                        "run_id": run_id,
                        "games": [g.model_dump(mode='json') for g in parsed_games],
                        "html_path": html_path,
                        "html_size_kb": len(html_content) / 1024,
                        "screenshot_path": screenshot_path,
                        "_validated": True  # Flag that data passed Pydantic
                    }
                except ValidationError as ve:
                    logger.error("Sensor output failed final validation", extra={
                        "event": "output_validation_failed", 
                        "run_id": run_id, 
                        "errors": str(ve)
                    })
                    raise Exception(f"Data validation failed: {ve}")
            
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                logger.error("Sensor run failed", extra={"event": "sensor_failed", "run_id": run_id, "error": str(e)})
                return None


if __name__ == "__main__":
    # Test run
    data = capture_session()
    if data:
        print(f"Success: Found {len(data['games'])} games.")
        print(f"Validated: {data.get('_validated', False)}")

