"""Detect the language / script of an SMS so explanations and fallbacks match it."""
import re

SCRIPT_RANGES = {
    "ta": (0x0B80, 0x0BFF),
    "hi": (0x0900, 0x097F),
    "bn": (0x0980, 0x09FF),
    "te": (0x0C00, 0x0C7F),
}
ROMAN_MARKERS = {
    "tanglish": {"unga", "ungal", "pannunga", "panni", "panna", "illa", "illai", "vandha", "vandhuduchu", "sollunga",
                 "irukku", "aagidum", "aagiduchu", "machan", "kitta", "inniku", "naalaiku", "anuppunga", "vendam",
                 "pannadheenga", "seekiram", "enna", "ellam", "romba", "da", "vaa", "thappa", "mosadi"},
    "hinglish": {"aapka", "aapke", "aap", "hai", "hain", "karo", "karein", "nahi", "bhejo", "mein", "hoga", "jaldi",
                 "kya", "kar", "ho", "gaya", "jayega", "bhai", "paise", "turant", "abhi", "yeh", "kisi"},
    "banglish": {"apnar", "korun", "hoyeche", "taka", "ami", "tomar", "ache", "kore", "pathao", "pathan", "hobe",
                 "ekhoni", "korben", "deben", "theke", "ebong"},
    "tenglish": {"mee", "meeru", "cheyandi", "ledu", "undi", "nundi", "chesi", "vachindi", "cheyadaniki", "kosam",
                 "dabbu", "pampandi", "ivvandi", "cheyakandi", "ippudu", "chala"},
}


def script_counts(text):
    counts = {k: 0 for k in SCRIPT_RANGES}
    counts["latin"] = 0
    for ch in text:
        o = ord(ch)
        for k, (lo, hi) in SCRIPT_RANGES.items():
            if lo <= o <= hi:
                counts[k] += 1
                break
        else:
            if ch.isascii() and ch.isalpha():
                counts["latin"] += 1
    return counts


def dominant_script(text):
    """'ta' | 'hi' | 'bn' | 'te' | 'latin' — a native script wins if it is >=20% of letters."""
    c = script_counts(text)
    total = sum(c.values()) or 1
    native = max(SCRIPT_RANGES, key=lambda k: c[k])
    return native if c[native] / total >= 0.2 else "latin"


def detect_language(text):
    """Returns one of: ta, hi, bn, te, en, tanglish, hinglish, banglish, tenglish."""
    s = dominant_script(text)
    if s != "latin":
        return s
    words = set(re.findall(r"[a-z]+", text.lower()))
    best, hits = "en", 0
    for lang, markers in ROMAN_MARKERS.items():
        n = len(words & markers)
        if n > hits:
            best, hits = lang, n
    return best if hits >= 2 else "en"


LANG_NAMES = {"ta": "Tamil", "hi": "Hindi", "bn": "Bengali", "te": "Telugu", "en": "English",
              "tanglish": "Tanglish", "hinglish": "Hinglish", "banglish": "Banglish", "tenglish": "Tenglish"}
