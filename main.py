import os
import json
import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
from urls_config import MANUAL_TARGET_URLS

OUTPUT_FILE = "live_data.json"

def scrape_match_data(source_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(source_url, timeout=30000)
            page.wait_for_load_timeout(3000)
            
            # DOM Text Extraction
            page_text = page.evaluate("() => document.body.innerText")
            
            # Yahan aap apna actual score/commentary parse karenge
            current_score = "185/4 (18.2 ov)"
            ball_event = "FOUR! Slog sweep over mid-wicket."

            return {
                "source_url": source_url,
                "score_summary": {"current_score": current_score},
                "latest_commentary": {"ball_event": ball_event}
            }
        except Exception as e:
            print(f"Scraping error for {source_url}: {e}")
            return None
        finally:
            browser.close()

def run_pipeline():
    print("--- GitHub Direct Pipeline Started ---")
    matches_data = []

    for url in MANUAL_TARGET_URLS:
        data = scrape_match_data(url)
        if data:
            matches_data.append(data)
        
        # Anti-block jitter delay
        time.sleep(random.uniform(2.0, 4.0))

    payload = {
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "total_matches": len(matches_data),
        "matches": matches_data
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(payload, f, indent=4)
    print("Data successfully saved to live_data.json")

if __name__ == "__main__":
    run_pipeline()
