# KAVACH — run the pipeline and dashboard

## Folder layout
```
kavach_app/
  app.py              Streamlit dashboard
  bench.py            KPI benchmark for the report (writes bench_results.json)
  setup_pi.sh         one-time setup on Raspberry Pi 5
  requirements.txt
  kavach/             pipeline code (stage1, stage2, link check, output checker, verified fallbacks)
  models/             Stage 1 model + tokenizer (included)
  models/llama/       PUT Stage 2 here: kavach_llama_fp16.pte + kavach_tokenizer/ folder
  data/               challenge_set.csv, challenge_set_2.csv (for bench.py)
```
Without the Stage-2 files the app still runs: explanations come from the verified templates.

## Raspberry Pi 5
```
bash setup_pi.sh
source ~/kavach-env/bin/activate
streamlit run app.py --server.address 0.0.0.0
```
Open `http://kavach.local:8501` from a laptop/phone on the same Wi-Fi, or a browser on the Pi itself.

Benchmark (for the report):
```
python bench.py              # Stage 1 + Stage 2
python bench.py --stage1-only
```

## Windows laptop
ExecuTorch has no Windows build, so use WSL (Ubuntu inside Windows):
1. Open PowerShell as admin → `wsl --install` → restart → open "Ubuntu".
2. Inside Ubuntu: `cd /mnt/c/Users/<you>/Downloads/kavach_app` then follow the Pi steps above
   (use `python3 -m venv`, `pip install -r requirements.txt`, `streamlit run app.py`).
3. Open `http://localhost:8501` in your Windows browser.

## How it works
1. **Stage 1** — IndicBERT INT8, vocab-pruned (37.5 MB, ExecuTorch/XNNPACK) → SCAM / GENUINE + confidence.
2. **Link check** — offline phishing-URL rules (fake bank domains, .xyz/.top, shorteners, IP links). A HIGH-risk link upgrades a GENUINE verdict to SCAM.
3. **Stage 2** — fine-tuned Llama 3.2 1B (FP16 ExecuTorch) explains the verdict in the SMS's own language, streamed word by word.
4. **Output checker** — rejects broken AI output (wrong script, repeats, cut-off, too few lines).
5. **Verified fallback** — hand-checked 3-line advice for 7 scam categories × 9 language variants.

## Network shield (tab 2) — demo
The Network tab learns normal traffic for 30 s, then raises alerts. To trigger them safely for the demo video,
open a second terminal on the Pi (`ssh` again, `source ~/kavach-env/bin/activate`, `cd ~/kavach_app`):
```
python simulate_attack.py scan        # -> PORT SCAN alert
python simulate_attack.py backdoor    # -> NEW LISTENER on port 4444 (malware/backdoor port)
python simulate_attack.py exfil       # -> TRAFFIC SPIKE (data-theft burst)
```
From your laptop on the same Wi-Fi you can also scan the Pi: `python simulate_attack.py scan --target kavach.local`
(or `nmap kavach.local` if nmap is installed) — the Pi detects it from the kernel's TCP reset counter.
