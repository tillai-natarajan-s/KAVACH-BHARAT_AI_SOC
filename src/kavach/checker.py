"""Validate the LLM explanation before showing it. Broken output -> verified fallback."""
import re
from .lang import dominant_script, script_counts


def clean(text):
    text = text.replace("\r", "").strip()
    text = re.sub(r"\s*\|\s*", "\n", text)            # model sometimes keeps the training ' | ' separator
    lines = [l.strip(" -•*\t") for l in text.split("\n")]
    return [l for l in lines if l]


def check(explanation, sms, truncated=False):
    """Returns (ok, reason, lines)."""
    if not explanation or not explanation.strip():
        return False, "empty output", []
    if "�" in explanation:
        # a cut multi-byte character usually means the answer was truncated
        explanation = explanation.split("�")[0]
        truncated = True
    lines = clean(explanation)
    if truncated and lines:
        lines = lines[:-1]                              # last line was cut mid-sentence
    if len(lines) < 2:
        return False, "fewer than 2 complete lines", lines
    lines = lines[:3]
    if len(set(lines)) < len(lines):
        return False, "repeated line", lines
    words = " ".join(lines).split()
    grams = [" ".join(words[i:i + 4]) for i in range(len(words) - 3)]
    if grams and max(grams.count(g) for g in set(grams)) >= 3:
        return False, "repeating phrase", lines
    want = dominant_script(sms)
    got = script_counts(" ".join(lines))
    letters = sum(got.values()) or 1
    if want != "latin" and got[want] / letters < 0.2:
        return False, f"wrong script (expected {want})", lines
    if want == "latin" and got["latin"] / letters < 0.6:
        return False, "wrong script (expected English letters)", lines
    if any(len(l) < 8 for l in lines):
        return False, "line too short", lines
    return True, "ok", lines
