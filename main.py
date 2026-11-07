import os
import json
import time
import random
import hashlib
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

from urls_config import MANUAL_TARGET_URLS

# --- YAHAN APNI CLOUDWAYS WEBSITE KA ENDPOINT AUR SECRET KEY DAALEIN ---
YOUR_CLOUDWAYS_ENDPOINT = "https://apni-cloudways-website.com/receive-score.php"
SECRET_KEY = "YOUR_SHARED_SECRET_KEY"

STATE_FILE = "last_sent_state.json"

def load_previous_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_current_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Error saving state file: {e}")

def discover_upcoming_or_live_matches_automatically():
    auto_discovered_urls = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://third-party-cricket-site.com/cricket-matches", timeout=30000)
            page.wait_for_load_timeout(3000)
            links = page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
            for link in links:
                if "/match/" in link:
                    auto_discovered_urls.append(link)
            browser.close()
        except Exception as e:
            print(f"Automatic discovery warning/error: {e}. Using manual URLs.")
            browser.close()
    return list(set(auto_discovered_urls))

def scrape_match_data(source_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(source_url, timeout=30000)
            page.wait_for_load_timeout(3000)
            
            # DOM Text Extraction (Copy restriction bypass)
            page_text = page.evaluate("() => document.body.innerText")
            
            # Yahan aap apna actual scoring text extract karenge
            current_score = "185/4 (18.2 ov)"
            ball_event = "FOUR! Slog sweep over mid-wicket."
            
            if not current_score or not ball_event:
                browser.close()
                return None

            refined_data = {
                "source_url": source_url,
                "is_live": True,
                "score_summary": {"current_score": current_score},
                "latest_commentary": {"ball_event": ball_event}
            }
            browser.close()
            return refined_data
        except Exception as e:
            print(f"Scraping error for {source_url}: {e}")
            browser.close()
            return None

def push_data_to_cloudways(payload, retries=3):
    for attempt in range(retries):
        try:
            response = requests.post(YOUR_CLOUDWAYS_ENDPOINT, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Push Attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    return None

def run_pipeline():
    print("--- Fully Automated Pipeline Started ---")
    
    auto_urls = discover_upcoming_or_live_matches_automatically()
    all_target_urls = list(set(MANUAL_TARGET_URLS + auto_urls))
    
    if not all_target_urls:
        print("No match URLs found to track. Exiting.")
        return

    previous_state = load_previous_state()
    matches_to_send = []
    new_state = {}

    for url in all_target_urls:
        data = scrape_match_data(url)
        if not data:
            continue
            
        if not data.get("is_live", True):
            continue
            
        state_string = f"{data['score_summary']['current_score']}_{data['latest_commentary']['ball_event']}"
        current_hash = hashlib.md5(state_string.encode()).hexdigest()
        url_hash_key = hashlib.md5(url.encode()).hexdigest()
        new_state[url_hash_key] = current_hash
        
        if previous_state.get(url_hash_key) == current_hash:
            print(f"No new update for {url}. Skipping.")
            continue
            
        matches_to_send.append(data)

        # Anti-block Jitter (2-4 seconds gap between matches)
        time.sleep(random.uniform(2.0, 4.0))

    if not matches_to_send:
        print("No new updates across matches. Zero requests sent.")
        save_current_state(new_state)
        return

    payload = {
        "secret_key": SECRET_KEY,
        "timestamp": datetime.utcnow().isoformat(),
        "total_matches": len(matches_to_send),
        "matches": matches_to_send
    }

    result = push_data_to_cloudways(payload)
    if result:
        print("Data successfully pushed to Cloudways:", result)
        save_current_state(new_state)
    else:
        print("Failed to push data after retries.")

if __name__ == "__main__":
    run_pipeline()
