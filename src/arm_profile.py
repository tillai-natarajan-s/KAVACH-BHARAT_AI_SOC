"""Arm hardware profile for the report: CPU features, core scaling of Stage 1 (1/2/4 Cortex-A76 cores
via taskset), throughput, SoC temperature, throttle flags and fan speed.
   python arm_profile.py      -> arm_profile.json   (about 3 minutes)"""
import glob
import json
import os
import subprocess
import sys
import time

CHILD = r'''
import csv, json, statistics, time, sys
sys.path.insert(0, ".")
from kavach.stage1 import Stage1
s = Stage1()
rows = list(csv.DictReader(open("data/challenge_set.csv", encoding="utf-8")))
col = next((c for c in ("text", "sms", "message", "Message", "SMS") if c in rows[0]), list(rows[0])[0])
texts = [r[col] for r in rows]
for t in texts[:10]: s.predict(t)                      # warm-up
lat = []; t0 = time.perf_counter()
for i in range(300):
    lat.append(s.predict(texts[i % len(texts)])["latency_ms"])
wall = time.perf_counter() - t0
lat.sort()
print(json.dumps({"p50_ms": round(statistics.median(lat), 2), "p95_ms": round(lat[int(0.95 * len(lat))], 2),
                  "mean_ms": round(statistics.mean(lat), 2), "msgs_per_s": round(300 / wall, 1)}))
'''


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


def temp_c():
    out = sh("vcgencmd measure_temp")          # temp=61.3'C
    try:
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        try:
            return int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000
        except Exception:
            return None


def fan_rpm():
    for f in glob.glob("/sys/devices/platform/cooling_fan/hwmon/*/fan1_input"):
        try:
            return int(open(f).read())
        except Exception:
            pass
    return None


def cpu_info():
    txt = open("/proc/cpuinfo").read()
    feats = ""
    for line in txt.splitlines():
        if line.lower().startswith("features"):
            feats = line.split(":", 1)[1].split()
            break
    part = next((l.split(":")[1].strip() for l in txt.splitlines() if "CPU part" in l), "")
    try:
        fmax = int(open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").read()) / 1e6
    except Exception:
        fmax = None
    want = {"asimd": "NEON / Advanced SIMD", "fphp": "FP16 scalar", "asimdhp": "FP16 SIMD",
            "asimddp": "INT8 dot product (SDOT/UDOT)", "lrcpc": "RCpc", "atomics": "LSE atomics"}
    return {"cpu_part": part + (" (Cortex-A76)" if part.lower() == "0xd0b" else ""),
            "cores": os.cpu_count(), "max_freq_ghz": fmax,
            "arm_features_used": {k: v for k, v in want.items() if k in feats},
            "governor": sh("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")}


res = {"cpu": cpu_info(), "before": {"temp_c": temp_c(), "fan_rpm": fan_rpm(),
                                    "throttled": sh("vcgencmd get_throttled")}, "stage1_core_scaling": {}}
print(json.dumps(res["cpu"], indent=2))
for n in (1, 2, 4):
    cores = "0" if n == 1 else f"0-{n - 1}"
    print(f"Stage 1 on {n} core(s) ...", flush=True)
    out = subprocess.run(["taskset", "-c", cores, sys.executable, "-c", CHILD],
                         capture_output=True, text=True, timeout=900)
    line = [l for l in out.stdout.splitlines() if l.startswith("{")]
    r = json.loads(line[-1]) if line else {"error": out.stderr[-400:]}
    r["temp_c_after"] = temp_c()
    res["stage1_core_scaling"][f"{n}_core"] = r
    print("  ", r, flush=True)
    time.sleep(5)
res["after"] = {"temp_c": temp_c(), "fan_rpm": fan_rpm(), "throttled": sh("vcgencmd get_throttled"),
                "arm_clock_hz": sh("vcgencmd measure_clock arm")}
json.dump(res, open("arm_profile.json", "w"), indent=2)
print(json.dumps({k: res[k] for k in ("before", "after")}, indent=2))
print("Saved arm_profile.json")
