import os
import json
import time
import random
import hashlib
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# Separate config file se manual URLs import kar rahe hain
from urls_config import MANUAL_TARGET_URLS

# --- CONFIGURATION (GITHUB SECRETS BEST PRACTICE) ---
# GitHub repository ke Secrets mein inke values set karein, ya yahan direct URL daal dein
YOUR_SECOND_WEBSITE_ENDPOINT = os.getenv("WEBSITE_ENDPOINT", "https://apni-dusri-website.com/api/receive-score.php")
SECRET_KEY = os.getenv("SECRET_KEY", "YOUR_SHARED_SECRET_KEY")

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
    """
    Automatic Discovery: Source website ke page se live/upcoming matches ke URLs 
    khud-b-hud dhoond kar list return karega.
    """
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
            print(f"Automatic discovery warning/error: {e}. Falling back to manual URLs.")
            browser.close()
            
    return list(set(auto_discovered_urls))

def scrape_match_data(source_url):
    """
    Rule 1: DOM Text Extraction (Bypass copy restrictions via innerText).
    Rule 2: Data Validation Guard (Ensuring extracted data is not empty/null).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(source_url, timeout=30000)
            page.wait_for_load_timeout(3000)
            
            # Copy restrictions bypass via innerText
            page_text = page.evaluate("() => document.body.innerText")
            
            # Simulated extracted fields (Aap yahan apna actual parsing/regex lagayenge)
            current_score = "185/4 (18.2 ov)"
            ball_event = "FOUR! Slog sweep over mid-wicket."
            
            # Data Validation Guard: Agar data khaali hai toh ignore karo
            if not current_score or not ball_event:
                print(f"Data validation failed for {source_url}. Incomplete data extracted.")
                browser.close()
                return None

            refined_data = {
                "source_url": source_url,
                "is_live": True,  # False hone par match skip ho jayega
                "score_summary": {
                    "current_score": current_score
                },
                "latest_commentary": {
                    "ball_event": ball_event
                }
            }
            browser.close()
            return refined_data
        except Exception as e:
            print(f"Scraping error for {source_url}: {e}")
            browser.close()
            return None

def push_data_to_second_website(payload, retries=3):
    """Rule: Retry Mechanism & Timeout ke sath one-way push"""
    for attempt in range(retries):
        try:
            response = requests.post(YOUR_SECOND_WEBSITE_ENDPOINT, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Push Attempt {attempt + 1} failed: {e}")
            time.sleep(2) # Chhota sa network retry pause
    return None

def run_pipeline():
    start_time = datetime.utcnow()
    print(f"--- Pipeline Execution Started at {start_time.isoformat()} ---")
    
    # Step 1: Gather URLs (Manual + Auto)
    auto_urls = discover_upcoming_or_live_matches_automatically()
    all_target_urls = list(set(MANUAL_TARGET_URLS + auto_urls))
    
    if not all_target_urls:
        print("No match URLs found to track. Exiting.")
        return

    previous_state = load_previous_state()
    matches_to_send = []
    new_state = {}

    # Stats counters for Execution Summary
    stats = {
        "total_checked": len(all_target_urls),
        "updated": 0,
        "skipped_duplicate": 0,
        "skipped_paused": 0,
        "failed_scrape": 0
    }

    for url in all_target_urls:
        data = scrape_match_data(url)
        if not data:
            stats["failed_scrape"] += 1
            continue
            
        # Rule: Match Paused / Finished Check
        if not data.get("is_live", True):
            print(f"Match at {url} is paused or finished. Skipping.")
            stats["skipped_paused"] += 1
            continue
            
        # Rule: Duplication Checker (MD5 Hash)
        state_string = f"{data['score_summary']['current_score']}_{data['latest_commentary']['ball_event']}"
        current_hash = hashlib.md5(state_string.encode()).hexdigest()
        
        url_hash_key = hashlib.md5(url.encode()).hexdigest()
        new_state[url_hash_key] = current_hash  # Active matches ka state store karo
        
        if previous_state.get(url_hash_key) == current_hash:
            print(f"No new update for {url}. Skipping (Duplicate).")
            stats["skipped_duplicate"] += 1
            continue
            
        matches_to_send.append(data)
        stats["updated"] += 1

        # Rule: Randomized Jitter / Anti-Block Protection (2 to 4 seconds gap between matches)
        jitter_delay = random.uniform(2.0, 4.0)
        print(f"Jitter pause: waiting {round(jitter_delay, 2)}s before next match...")
        time.sleep(jitter_delay)

    # Step 2: Push data if updates exist
    if not matches_to_send:
        print("No new updates across matches. Zero requests sent.")
        save_current_state(new_state)
        print_summary(stats, start_time, sent=False)
        return

    payload = {
        "secret_key": SECRET_KEY,
        "timestamp": datetime.utcnow().isoformat(),
        "total_matches": len(matches_to_send),
        "matches": matches_to_send
    }

    # Step 3: One-way push to your second website API
    result = push_data_to_second_website(payload)
    if result:
        print("Data successfully pushed to your second website:", result)
        save_current_state(new_state)
        print_summary(stats, start_time, sent=True)
    else:
        print("Failed to push data after retries.")

def print_summary(stats, start_time, sent):
    """Execution Summary Logger for clear background insights"""
    end_time = datetime.utcnow()
    duration = (end_time - start_time).seconds
    print("\n--- EXECUTION SUMMARY REPORT ---")
    print(f"Total Matches Checked : {stats['total_checked']}")
    print(f"Updates Sent to API   : {stats['updated']}")
    print(f"Skipped (Duplicates)  : {stats['skipped_duplicate']}")
    print(f"Skipped (Paused/Done) : {stats['skipped_paused']}")
    print(f"Failed / Scrape Errors: {stats['failed_scrape']}")
    print(f"API Payload Sent      : {'Yes' if sent else 'No'}")
    print(f"Execution Duration    : {duration} seconds")
    print("----------------------------------\n")

if __name__ == "__main__":
    run_pipeline()
