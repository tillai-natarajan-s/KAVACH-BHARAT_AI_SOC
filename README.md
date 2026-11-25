# KAVACH — offline, on-device multilingual scam & threat shield (Raspberry Pi 5)

**Team Iconic · Dept. of ECE, Chennai Institute of Technology**
Bharat AI-SoC Challenge 2026-27 · **PS3: Cybersecurity & Digital Safety** (on-device threat, phishing & scam detection)

KAVACH ("armour") reads an SMS, decides if it is a scam, checks every link in it, and explains the verdict in
**three short lines in the same language and script as the SMS** — Tamil, Hindi, Bengali, Telugu, English and the
romanised mixes people really type (Tanglish, Hinglish, Banglish, Tenglish). A second tab watches the home network for
port scans, data-theft bursts, backdoor ports and new devices joining the Wi-Fi. **Everything runs on a Raspberry Pi 5
(4× Arm Cortex-A76) with no internet.**

Built with Llama.

---

## Results measured on the Raspberry Pi 5

| What | Result |
|---|---|
| Scam verdict (Stage 1, IndicBERT INT8, ExecuTorch + XNNPACK) | **38.3 ms** p50 · 38.4 ms p95 · 25.6 SMS/s |
| Model size | **38.2 MB** (from a 516 MB baseline, 14× smaller) |
| Hand-written challenge set 1 (140 SMS, 7 languages) | **0.879** accuracy |
| Challenge set 2 — scam types **never seen in training** (140 SMS) | **0.929** accuracy, **0 scams missed** |
| Public UCI SMS Spam (5,171 UK English SMS, never trained on) | 81% of spam caught, 13% false alarms (different country/decade) |
| Explanation (Stage 2, Llama 3.2 1B + LoRA, FP16 .pte) | first word in **1.6–2.7 s**, **4.3–4.5 tok/s**, output check 8/8 |
| Core scaling, Stage 1 | 1 core 103.9 ms → 2 cores 58.2 ms → 4 cores **38.6 ms** |
| Phishing links: offline OpenPhish copy + rules | 298/298 feed URLs blocked offline; rules alone flag 73.5% of live phishing; 0/114 popular legit sites flagged |
| Network shield | port scan (66 probes/s), backdoor port 4444, 100 MB/s exfiltration spike, new phones joining Wi-Fi (instant, by DHCP) — all detected live |

Raw numbers: [`results/`](results/) (`bench_results.json`, `arm_profile.json`, `uci_results.json`, `link_eval_results.json`).

## How it works

```
SMS ─► Stage 1: IndicBERT INT8 (.pte, XNNPACK)  ─► SCAM / GENUINE + confidence      (38 ms)
   └─► Link check: offline OpenPhish copy + look-alike rules ─► HIGH link turns GENUINE into SCAM
                     │
                     ▼
        Stage 2: Llama 3.2 1B + LoRA (FP16 .pte) ─► 3-line explanation in the SMS's own language, streamed
                     │                               (1 why · 2 what NOT to do · 3 what to do / 1930)
                     ▼
        Output checker ─► pass: AI text  |  fail: verified fallback (7 categories × 9 language variants)

Network shield (background, 1 s): psutil + /proc/net/snmp + ARP + DHCP join broadcasts
   → PORT_SCAN · TRAFFIC_SPIKE · CONN_SURGE · SUSPICIOUS_PORT · NEW_LISTENER · NEW_DEVICE
Dashboard: Streamlit, live Arm stats (latency, tok/s, RAM, CPU, SoC temp), offline badge, history
```

* **Stage 1 decides, Stage 2 only explains.** Llama is told the verdict (`Classifier verdict: SCAM`), so the
  explanation can never contradict what the user sees.
* **Why FP16 for Llama:** post-training 4-bit (8da4w) erased the Tamil/Telugu/Bengali fine-tune (gibberish), while
  FP16 is identical to the GPU model, fits the 8 GB Pi and runs on the Cortex-A76's native FP16 units.
  4-bit via quantization-aware training is the Phase 2 plan.
* **Arm features used** (from `/proc/cpuinfo` on the Pi): NEON/ASIMD, FP16 scalar + SIMD, INT8 dot product (SDOT/UDOT).

## Repository layout

```
src/                     the KAVACH app (copy this folder to the Pi)
  app.py                 Streamlit dashboard (SMS & link shield · Network shield)
  kavach/                stage1.py · stage2.py · pipeline.py · checker.py · fallback.py · lang.py
                         urlcheck.py (links) · netmon.py (traffic) · netdevices.py (Wi-Fi devices)
  models/                Stage 1 .pte (v3) + tokenizer + kavach_meta.json   (Llama goes in models/llama/)
  data/                  challenge_set.csv, challenge_set_2.csv (hand-written, never trained on)
  setup_pi.sh            one-shot setup (apt + venv + pip)
  bench.py               KPI benchmark → bench_results.json
  arm_profile.py         Arm CPU features + 1/2/4-core scaling + temperature/fan
  eval_uci.py            external test on the UCI SMS Spam Collection
  update_feed.py         download OpenPhish feed for offline use
  eval_links.py          link-checker accuracy (rules vs feed, phishing vs legit)
  simulate_attack.py     SAFE local attack simulator: scan | exfil | backdoor
  README_RUN.md          more run notes
DATA/                    synthetic Indian SMS training data (7 languages, 41 CSVs)
results/                 all measured KPIs (JSON + logs)
```

## Run it on a Raspberry Pi 5

Tested on Raspberry Pi 5 (8 GB), Raspberry Pi OS 64-bit (Debian 13, kernel 6.18), Python 3.13, ExecuTorch 1.6.

```bash
git clone https://github.com/tillai-natarajan-s/KAVACH-BHARAT_AI_SOC.git
cd KAVACH-BHARAT_AI_SOC/src
bash setup_pi.sh                                   # venv ~/kavach-env + requirements
```

**Llama model (2.8 GB, too big for GitHub):** download `kavach_llama_fp16.pte` and the `kavach_tokenizer/` folder from
**LLAMA_DOWNLOAD_LINK** and put them in `src/models/llama/`.
Without it KAVACH still runs: explanations come from the verified fallback messages.

```bash
source ~/kavach-env/bin/activate
python update_feed.py          # optional, needs internet once: offline OpenPhish copy
# optional: lets the Wi-Fi watch hear DHCP join broadcasts on port 67 without running as root
sudo setcap 'cap_net_bind_service=+ep' $(readlink -f ~/kavach-env/bin/python)

streamlit run app.py --server.address 0.0.0.0      # open http://<pi-ip>:8501
```

Reproduce the numbers:

```bash
python bench.py --stage1-only   # Stage 1 latency + both challenge sets
python bench.py                 # + Llama TTFT, tok/s, output-check pass rate
python arm_profile.py           # Arm features, 1/2/4-core scaling, temperature
python eval_uci.py              # public UCI SMS Spam test
python eval_links.py            # link checker vs OpenPhish + legit sites
```

Network demo (from the Pi or a laptop on the same Wi-Fi; only touches your own device):

```bash
python simulate_attack.py scan       # → PORT SCAN
python simulate_attack.py backdoor   # → NEW LISTENER on 4444
python simulate_attack.py exfil      # → TRAFFIC SPIKE
# connect a new phone to the Wi-Fi  → NEW DEVICE (name + Android version, via DHCP)
```

## How the models were made

* **Stage 1** — `ai4bharat/indic-bert` fine-tuned on 9,984 synthetic Indian SMS (`DATA/`), 3 epochs, lr 3e-5,
  label smoothing 0.1 → vocabulary pruned 200,000 → 55,354 tokens (id map baked into the model) → PT2E dynamic
  INT8 (XNNPACKQuantizer, per-channel) → ExecuTorch with XNNPACK partitioner, sequence length 64.
* **Stage 2** — Llama 3.2 1B Instruct + LoRA (r 16, α 32, all attention + MLP projections, 0.9% of weights) on
  2,190 SMS→explanation pairs in 13 language variants, 5 epochs on a Kaggle T4 → merged → Meta checkpoint layout →
  `executorch.examples.models.llama.export_llama -kv --use_sdpa_with_kv_cache -X -d fp16 --max_seq_length 1024`.

## Known limitations (honest)

* Stage 1 still misses some native-script scams with no link (e.g. Telugu power-cut threat, Tamil prize fee) and
  "earn by liking videos" job scams; it raises false alarms on some genuine transaction SMS (refund, FASTag,
  insurance, salary).
* Training data is synthetic; both challenge sets are hand-written and unseen, but not real inbox messages.
* Llama decode (~4.4 tok/s) is memory-bandwidth bound in FP16, so Indic explanations take 20–60 s to finish
  streaming (first words in ~2 s).
* Wi-Fi watch: the DHCP sensor catches devices as they join; a device that joined before KAVACH started and stays
  silent is only seen once it talks. It watches this network segment only.
* Scam *calls* are not covered yet.

## Phase 2

4-bit Llama via quantization-aware training (~3× faster decode) · real SMS test set (with consent) · C++ ExecuTorch
runner · Android app reading incoming SMS · power measurement · scam-call screening.

## Credits & licences

Base models: [ai4bharat/indic-bert](https://huggingface.co/ai4bharat/indic-bert),
[meta-llama/Llama-3.2-1B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct) — used under the
Llama 3.2 Community License (Built with Llama). Runtime: [ExecuTorch](https://github.com/pytorch/executorch) with
XNNPACK. Threat feed: [OpenPhish](https://openphish.com) community feed (downloaded by the user, not redistributed).
External test set: UCI SMS Spam Collection (Almeida & Hidalgo, 2011), downloaded at run time.
