# urls_config.py
# Ab aapko quotes ya commas lagane ki koi zaroorat nahi hai.
# Bas apne match ke URLs ko ek ke baad ek naye line mein paste kar dijiye:

_raw_urls = """
https://third-party-cricket-site.com/match/upcoming-match-1
https://third-party-cricket-site.com/match/upcoming-match-2
https://third-party-cricket-site.com/match/upcoming-match-3
"""

# Yeh code apne aap saare URLs ko read karke set kar lega (Aapko is line ko chhoone ki zaroorat nahi)
MANUAL_TARGET_URLS = [url.strip() for url in _raw_urls.strip().splitlines() if url.strip()]
