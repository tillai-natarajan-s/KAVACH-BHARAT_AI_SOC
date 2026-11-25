"""KAVACH benchmark — produces the KPI numbers for the engineering report.

Usage:
  python bench.py                          # Stage 1 on both challenge sets + Stage 2 on 8 test messages
  python bench.py --stage1-only
  python bench.py --challenge data/challenge_set.csv data/challenge_set_2.csv
Writes bench_results.json.
"""
import argparse, json, os, platform, statistics, time
import pandas as pd
import psutil

from kavach import config
from kavach.lang import detect_language

TESTS = [
    ("உங்கள் வங்கி கணக்கு இன்று முடக்கப்படும். உடனே KYC அப்டேட் செய்யுங்கள்.", "SCAM"),
    ("Ippo unga phone ku vandha OTP sollunga, thappa unga number ku vandhuduchu", "SCAM"),
    ("Main army officer hoon, aapka saman khareedna hai, pehle 1 rupaya bhejo confirm karne ke liye", "SCAM"),
    ("आपका बिजली कनेक्शन आज रात काट दिया जाएगा, तुरंत इस नंबर पर कॉल करें।", "SCAM"),
    ("Your FASTag recharge of Rs 500 is successful. Balance Rs 742.", "GENUINE"),
    ("মা, আমার ফোন ভেঙে গেছে, এটা নতুন নম্বর। জরুরি ১০০০০ টাকা পাঠাও।", "SCAM"),
    ("మీ కరెంట్ కనెక్షన్ ఈరోజు రాత్రి కట్ చేయబడుతుంది, గత నెల బిల్ అప్‌డేట్ కాలేదు.", "SCAM"),
    ("நாளைக்கு காலேஜ் லீவு, பரீட்சை திங்கள்கிழமை.", "GENUINE"),
]


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--challenge", nargs="*", default=["data/challenge_set.csv", "data/challenge_set_2.csv"])
    ap.add_argument("--stage1-only", action="store_true")
    a = ap.parse_args()
    proc = psutil.Process(os.getpid())
    res = {"device": platform.machine(), "platform": platform.platform(), "cpus": psutil.cpu_count(),
           "total_ram_gb": round(psutil.virtual_memory().total / 1e9, 1)}

    from kavach.stage1 import Stage1
    t = time.perf_counter(); s1 = Stage1(); res["stage1_load_s"] = round(time.perf_counter() - t, 2)
    res["stage1_model_mb"] = round(os.path.getsize(config.STAGE1_PTE) / 1e6, 1)
    lat = []
    for _ in range(100):
        lat.append(s1.predict("Your SBI account will be blocked today, update KYC now")["latency_ms"])
    res["stage1_latency_ms"] = {"p50": round(pct(lat, 50), 1), "p95": round(pct(lat, 95), 1),
                                "mean": round(statistics.mean(lat), 1)}
    for path in a.challenge:
        if not os.path.exists(path):
            print("skip (not found):", path); continue
        df = pd.read_csv(path, encoding="utf-8-sig")
        pred = [1 if s1.predict(t)["verdict"] == "SCAM" else 0 for t in df.text]
        df["pred"] = pred
        acc = (df.pred == df.label).mean()
        per = {lang: round((g.pred == g.label).mean(), 3) for lang, g in df.groupby("language")}
        res[os.path.basename(path)] = {"accuracy": round(acc, 3),
                                       "missed_scams": int(((df.label == 1) & (df.pred == 0)).sum()),
                                       "false_alarms": int(((df.label == 0) & (df.pred == 1)).sum()),
                                       "per_language": per}
    res["ram_after_stage1_mb"] = round(proc.memory_info().rss / 1e6)
    print(json.dumps(res, indent=2, ensure_ascii=False))

    if not a.stage1_only and os.path.exists(config.STAGE2_PTE):
        from kavach.stage2 import Stage2
        from kavach.checker import check
        t = time.perf_counter(); s2 = Stage2(); res["stage2_load_s"] = round(time.perf_counter() - t, 2)
        res["stage2_model_mb"] = round(os.path.getsize(config.STAGE2_PTE) / 1e6, 1)
        runs = []
        for sms, v in TESTS:
            text, st = "", {}
            for text, st in s2.stream(sms, v):
                pass
            ok, reason, _ = check(text, sms, st.get("truncated", False))
            runs.append({"lang": detect_language(sms), "verdict": v, "ttft_s": round(st["ttft_s"], 2),
                         "tok_s": round(st["tok_s"], 2), "new_tokens": st["new_tokens"], "check": reason,
                         "batch_prefill": st["batch_prefill"], "text": text})
            print(f"[{v}] {sms}\n---> {text}\n[{st['ttft_s']:.1f}s first token | {st['tok_s']:.1f} tok/s | check: {reason}]\n")
        res["stage2_runs"] = runs
        res["stage2_tok_s_mean"] = round(statistics.mean(r["tok_s"] for r in runs), 2)
        res["stage2_ttft_mean_s"] = round(statistics.mean(r["ttft_s"] for r in runs), 2)
        res["stage2_check_pass"] = f"{sum(r['check'] == 'ok' for r in runs)}/{len(runs)}"
        res["ram_after_stage2_mb"] = round(proc.memory_info().rss / 1e6)
    json.dump(res, open("bench_results.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("\nSaved bench_results.json")


if __name__ == "__main__":
    main()
