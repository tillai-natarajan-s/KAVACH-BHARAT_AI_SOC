"""Phishing link check for links inside an SMS. Fully offline.
Two layers:
  1. Offline threat feed: a saved copy of the OpenPhish phishing-URL feed (models/threat_feed/openphish.txt).
     Refresh it with `python update_feed.py` whenever the device has internet; checks never need internet.
  2. Rules: official-domain whitelist, brand look-alikes, risky TLDs, shorteners, raw IPs, punycode, bait words.
"""
import json
import os
import re

URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"']+|\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?(?:/[^\s]*)?|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|in|co\.in|net|org|xyz|top|"
                    r"info|online|site|live|click|link|shop|app|ly|gl|me|io|cc|tk|ml|ga|cf|gq|buzz|vip|icu|cn|ru|biz|"
                    r"club|pro|gov\.in|nic\.in|bank\.in)\b(?:/[^\s]*)?", re.I)

OFFICIAL = {"sbi.co.in", "onlinesbi.sbi", "sbi.bank.in", "hdfcbank.com", "icicibank.com", "axisbank.com",
            "kotak.com", "pnbindia.in", "bankofbaroda.in", "canarabank.com", "unionbankofindia.co.in",
            "iob.in", "indianbank.in", "npci.org.in", "paytm.com", "phonepe.com", "amazon.in", "flipkart.com",
            "myntra.com", "irctc.co.in", "incometax.gov.in", "uidai.gov.in", "india.gov.in", "cybercrime.gov.in",
            "tnebnet.org", "tangedco.org", "bsesdelhi.com", "wbsedcl.in", "cesc.co.in", "tssouthernpower.com",
            "apspdcl.in", "fastag.ihmcl.com", "ihmcl.co.in", "npci.org", "youtube.com", "google.com",
            "forms.gle", "whatsapp.com", "swiggy.com", "zomato.com", "jio.com", "airtel.in",
            # v2: official sites the first version wrongly flagged
            "rbi.org.in", "licindia.in", "sbicard.com", "jiocinema.com", "amazon.com"}
BRANDS = ["sbi", "hdfc", "icici", "axis", "kotak", "pnb", "canara", "iob", "paytm", "phonepe", "gpay", "upi", "npci",
          "amazon", "flipkart", "myntra", "irctc", "aadhaar", "uidai", "incometax", "kyc", "fastag", "tneb",
          "bses", "electricity", "customs", "rbi", "lic", "epfo", "kbc", "jio", "airtel"]
RISKY_TLDS = {"xyz", "top", "info", "online", "site", "live", "click", "link", "shop", "buzz", "vip", "icu",
              "tk", "ml", "ga", "cf", "gq", "cn", "ru", "club"}
SHORTENERS = {"bit.ly", "tinyurl.com", "cutt.ly", "is.gd", "t.ly", "rb.gy", "shorturl.at", "ow.ly", "tiny.cc"}
LURE_WORDS = ["kyc", "verify", "update", "refund", "reward", "claim", "prize", "unlock", "secure", "login", "bonus"]
# Big shared hosts: scammers put pages on them, but the host name alone must not be blocked
# (only an exact URL listed in the feed is blocked there).
SHARED_HOSTS = {"docs.google.com", "sites.google.com", "drive.google.com", "storage.googleapis.com",
                "firebasestorage.googleapis.com", "github.com", "raw.githubusercontent.com", "dropbox.com",
                "onedrive.live.com", "1drv.ms", "t.co", "ipfs.io", "cloudflare-ipfs.com", "dweb.link",
                "web.app", "firebaseapp.com", "pages.dev", "github.io", "vercel.app", "netlify.app",
                "weebly.com", "wixsite.com", "blogspot.com", "sharepoint.com", "linkedin.com", "facebook.com",
                "instagram.com", "telegram.me", "t.me", "wa.me"} | SHORTENERS

FEED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "threat_feed")


def _domain(url):
    d = re.sub(r"^(https?://)?(www\.)?", "", url.lower()).split("/")[0].split(":")[0].split("?")[0]
    return d.strip(".,;)")


def _norm(url):
    u = re.sub(r"^(https?://)?(www\.)?", "", url.strip().lower())
    return u.rstrip("/.,;)")


def _brand_in(d):
    """v2: match a brand only as a whole word part of the name ("sbi-kyc", "hdfcnetbank"),
    not hidden inside another word ("ajio" is not "jio", "policybazaar" is not "lic")."""
    tokens = re.split(r"[.\-]", d)
    for b in BRANDS:
        for t in tokens:
            if t == b or t.startswith(b) or (len(b) >= 4 and b in t):
                return b
    return None


def _is_official(d):
    return any(d == o or d.endswith("." + o) for o in OFFICIAL) or d.endswith(".gov.in") or d.endswith(".nic.in") \
        or d.endswith(".bank.in")


def _load_feed():
    urls, hosts, meta = set(), set(), {}
    try:
        with open(os.path.join(FEED_DIR, "openphish.txt"), encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line.lower().startswith("http"):
                    continue
                urls.add(_norm(line))
                h = _domain(line)
                if h and h not in SHARED_HOSTS and not _is_official(h):
                    hosts.add(h)
    except FileNotFoundError:
        pass
    try:
        with open(os.path.join(FEED_DIR, "feed_meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (FileNotFoundError, ValueError):
        pass
    return urls, hosts, meta


FEED_URLS, FEED_HOSTS, FEED_META = _load_feed()


def feed_info():
    """For the dashboard / report: how many entries and when the offline copy was taken."""
    return {"urls": len(FEED_URLS), "hosts": len(FEED_HOSTS), "date": FEED_META.get("downloaded_utc", "unknown"),
            "source": FEED_META.get("source", "OpenPhish")}


def check_links(sms, use_feed=True):
    """Returns a list of {url, domain, risk: HIGH|MEDIUM|LOW, reasons:[...], in_feed: bool}."""
    found = []
    for m in URL_RE.finditer(sms):
        url = m.group(0).rstrip(".,;)")
        d = _domain(url)
        if not d or "." not in d:
            continue
        in_feed = use_feed and (_norm(url) in FEED_URLS or d in FEED_HOSTS)
        if _is_official(d) and not in_feed:
            found.append({"url": url, "domain": d, "risk": "LOW", "reasons": ["official domain"], "in_feed": False})
            continue
        reasons, score = [], 0
        if in_feed:
            score += 10
            reasons.append(f"listed in the OpenPhish phishing feed "
                           f"(offline copy, {FEED_META.get('downloaded_utc', '')[:10]})")
        tld = d.rsplit(".", 1)[-1]
        if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", d):
            score += 3; reasons.append("raw IP address instead of a website name")
        if d.startswith("xn--") or ".xn--" in d:
            score += 3; reasons.append("disguised (punycode) characters")
        if d in SHORTENERS:
            score += 2; reasons.append("link shortener hides the real website")
        if tld in RISKY_TLDS:
            score += 2; reasons.append(f"cheap '.{tld}' domain often used by scammers")
        brand = _brand_in(d)
        if brand and not _is_official(d):
            score += 3; reasons.append(f"uses the name '{brand}' but is NOT the official website")
        if any(w in d for w in LURE_WORDS):
            score += 1; reasons.append("bait word in the website name")
        if d.count("-") >= 2:
            score += 1; reasons.append("many hyphens in the website name")
        risk = "HIGH" if score >= 3 else "MEDIUM" if score >= 1 else "LOW"
        found.append({"url": url, "domain": d, "risk": risk, "reasons": reasons or ["unknown website"],
                      "in_feed": bool(in_feed)})
    return found
