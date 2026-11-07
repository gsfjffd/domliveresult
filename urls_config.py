# urls_config.py
# Ab aapko quotes ya commas lagane ki koi zaroorat nahi hai.
# Bas apne match ke URLs ko ek ke baad ek naye line mein paste kar dijiye:

_raw_urls = """
https://www.cricbuzz.com/live-cricket-scores/161256/nz-vs-ind-2nd-odi-india-tour-of-new-zealand-2026
https://www.cricbuzz.com/live-cricket-scores/162797/mlrw-vs-adsw-13th-match-womens-big-bash-league-2026
"""

# Yeh code apne aap saare URLs ko read karke set kar lega (Aapko is line ko chhoone ki zaroorat nahi)
MANUAL_TARGET_URLS = [url.strip() for url in _raw_urls.strip().splitlines() if url.strip()]
