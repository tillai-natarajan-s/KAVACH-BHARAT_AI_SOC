"""Download the OpenPhish community phishing feed and save it for OFFLINE use.
Run only when the device has internet:   python update_feed.py
Link checks afterwards work with no network (air-gapped)."""
import datetime
import json
import os
import urllib.request

SRC = "https://openphish.com/feed.txt"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "threat_feed")
os.makedirs(OUT, exist_ok=True)

print("Downloading", SRC, "...")
req = urllib.request.Request(SRC, headers={"User-Agent": "KAVACH-offline-feed/1.0"})
try:
    raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
except Exception as e:
    raise SystemExit(f"Download failed ({e}). Check internet; the old offline copy (if any) is kept.")

urls = sorted({l.strip() for l in raw.splitlines() if l.strip().lower().startswith("http")})
if len(urls) < 50:
    raise SystemExit(f"Feed looks wrong (only {len(urls)} URLs). Not saved.")

with open(os.path.join(OUT, "openphish.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(urls) + "\n")
meta = {"source": "OpenPhish community feed", "url": SRC, "count": len(urls),
        "downloaded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
with open(os.path.join(OUT, "feed_meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
print(f"Saved {len(urls)} phishing URLs -> {OUT}/openphish.txt")
print(json.dumps(meta, indent=2))
