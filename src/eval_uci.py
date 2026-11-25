"""External test: run the Stage 1 classifier (no retraining) on the public UCI SMS Spam Collection
(5,574 English SMS, mostly UK, 2012). Never used for training.
   python eval_uci.py      -> uci_results.json"""
import io
import json
import os
import statistics
import time
import urllib.request
import zipfile
from kavach.stage1 import Stage1

URL = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
DATA = os.path.join("data", "uci_sms")
PATH = os.path.join(DATA, "SMSSpamCollection")

if not os.path.exists(PATH):
    os.makedirs(DATA, exist_ok=True)
    print("Downloading UCI SMS Spam Collection ...")
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(URL, timeout=120).read()))
    z.extract("SMSSpamCollection", DATA)

rows = []
for line in open(PATH, encoding="utf-8", errors="ignore"):
    if "\t" in line:
        lab, txt = line.rstrip("\n").split("\t", 1)
        rows.append((1 if lab == "spam" else 0, txt))
uniq = list({t: (y, t) for y, t in rows}.values())
print(f"{len(rows)} SMS ({len(uniq)} unique). Loading Stage 1 ...")

s1 = Stage1()
preds, lat = {}, []
t0 = time.time()
for i, (y, t) in enumerate(uniq):
    r = s1.predict(t)
    preds[t] = 1 if r["verdict"] == "SCAM" else 0
    lat.append(r["latency_ms"])
    if (i + 1) % 500 == 0:
        print(f"  {i + 1}/{len(uniq)}  ({time.time() - t0:.0f}s)")


def metrics(data):
    tp = sum(1 for y, t in data if y == 1 and preds[t] == 1)
    fn = sum(1 for y, t in data if y == 1 and preds[t] == 0)
    fp = sum(1 for y, t in data if y == 0 and preds[t] == 1)
    tn = sum(1 for y, t in data if y == 0 and preds[t] == 0)
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    return {"n": len(data), "spam": tp + fn, "ham": fp + tn, "accuracy": round((tp + tn) / len(data), 4),
            "spam_recall": round(r, 4), "precision": round(p, 4),
            "f1": round(2 * p * r / (p + r), 4) if p + r else 0,
            "ham_false_alarm_rate": round(fp / (fp + tn), 4), "missed_spam": fn, "false_alarms": fp}


res = {"dataset": "UCI SMS Spam Collection (English, UK, 2012) - external, never trained on",
       "all_rows": metrics(rows), "unique_rows": metrics(uniq),
       "latency_ms": {"mean": round(statistics.mean(lat), 1), "p50": round(statistics.median(lat), 1)},
       "missed_spam_examples": [t for y, t in uniq if y == 1 and preds[t] == 0][:10],
       "false_alarm_examples": [t for y, t in uniq if y == 0 and preds[t] == 1][:10]}
json.dump(res, open("uci_results.json", "w"), indent=2, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if "examples" not in k}, indent=2))
print("\nSaved uci_results.json")
