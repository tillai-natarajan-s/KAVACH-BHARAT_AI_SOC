"""KAVACH dashboard — run with:  streamlit run app.py --server.address 0.0.0.0"""
import html
import os
import platform
import socket
import time

import psutil
import streamlit as st

from kavach import config  # noqa: F401  (loads paths / settings)
from kavach.lang import LANG_NAMES
from kavach.urlcheck import feed_info

st.set_page_config(page_title="KAVACH · on-device scam shield", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="collapsed")

# ------------------------------------------------------------------ style
st.markdown("""
<style>
:root{--bg:#070b14;--card:#0e1524;--card2:#121b2e;--line:#1f2a40;--txt:#e6edf7;--mute:#8a97ad;
      --cyan:#22d3ee;--red:#ff4d5e;--green:#2ee59d;--amber:#ffb020;}
html,body,[data-testid="stAppViewContainer"]{background:
   radial-gradient(1200px 600px at 10% -10%,rgba(34,211,238,.10),transparent 60%),
   radial-gradient(900px 500px at 100% 0%,rgba(255,77,94,.07),transparent 60%),var(--bg)!important;color:var(--txt)}
[data-testid="stHeader"]{background:transparent} #MainMenu,footer{visibility:hidden}
.block-container{padding-top:1.4rem;max-width:1400px}
*{font-family:Inter,"Noto Sans","Noto Sans Tamil","Noto Sans Devanagari","Noto Sans Bengali","Noto Sans Telugu",sans-serif}
h1,h2,h3,h4{color:var(--txt)!important}

/* hero */
.hero{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;
      background:linear-gradient(135deg,rgba(34,211,238,.10),rgba(14,21,36,.9));border:1px solid var(--line);
      border-radius:20px;padding:18px 24px;margin-bottom:14px}
.brand{display:flex;align-items:center;gap:16px}
.brand .name{font-size:2.3rem;font-weight:800;letter-spacing:.18em;line-height:1}
.brand .tag{color:var(--mute);font-size:.92rem;margin-top:6px}
.chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:7px;padding:7px 13px;border-radius:999px;font-size:.82rem;font-weight:600;
      background:var(--card2);border:1px solid var(--line);color:var(--txt)}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.dot.g{background:var(--green);box-shadow:0 0 10px var(--green);animation:pulse 1.6s infinite}
.dot.a{background:var(--amber);box-shadow:0 0 10px var(--amber)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}

/* tabs */
[data-baseweb="tab-list"]{gap:8px;background:var(--card);padding:6px;border-radius:14px;border:1px solid var(--line)}
[data-baseweb="tab"]{border-radius:10px!important;padding:8px 18px!important;color:var(--mute)!important;font-weight:600}
[data-baseweb="tab"][aria-selected="true"]{background:var(--card2)!important;color:var(--cyan)!important}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none}

/* panels */
.panel-title{font-size:.78rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--mute);margin:4px 0 10px}
[class*="st-key-panel"]{background:var(--card)!important;border:1px solid var(--line)!important;border-radius:18px!important;padding:16px 18px!important}
[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
button[role="tab"]{border-radius:10px!important;padding:8px 18px!important;font-weight:600}
button[role="tab"][aria-selected="true"]{background:var(--card2)!important}
button[role="tab"] p{font-size:1rem!important}
.stButton>button{border-radius:12px;border:1px solid var(--line);background:var(--card2);color:var(--txt);font-weight:600}
.stButton>button:hover{border-color:var(--cyan);color:var(--cyan)}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#0891b2,#22d3ee);color:#00131a;border:none;
      font-size:1.05rem;padding:.7rem 0;box-shadow:0 8px 24px rgba(34,211,238,.25)}
textarea{background:var(--card2)!important;color:var(--txt)!important;border-radius:12px!important;font-size:1.05rem!important}

/* tiles */
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.tile{background:var(--card2);border:1px solid var(--line);border-radius:14px;padding:12px 14px}
.tile .v{font-size:1.65rem;font-weight:800;line-height:1.1}
.tile .l{font-size:.74rem;color:var(--mute);text-transform:uppercase;letter-spacing:.08em;margin-top:4px}
.tile .s{font-size:.75rem;color:var(--mute)}
.bar{height:5px;border-radius:9px;background:#1c2740;margin-top:8px;overflow:hidden}
.bar>i{display:block;height:100%;border-radius:9px}

/* verdict */
.verdict{border-radius:20px;padding:20px 24px;margin:4px 0 12px;position:relative;overflow:hidden}
.verdict.scam{background:linear-gradient(135deg,rgba(255,77,94,.28),rgba(255,77,94,.06));border:1px solid rgba(255,77,94,.55)}
.verdict.safe{background:linear-gradient(135deg,rgba(46,229,157,.22),rgba(46,229,157,.05));border:1px solid rgba(46,229,157,.5)}
.verdict .big{font-size:2.7rem;font-weight:800;letter-spacing:.06em;line-height:1}
.verdict.scam .big{color:var(--red)} .verdict.safe .big{color:var(--green)}
.verdict .sub{color:var(--txt);opacity:.85;margin-top:8px}
.conf{height:8px;border-radius:9px;background:rgba(255,255,255,.08);margin-top:12px;overflow:hidden}
.conf>i{display:block;height:100%}

/* pipeline trace */
.trace{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:6px 0 14px}
.step{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:7px 11px;font-size:.8rem}
.step b{display:block;font-size:.92rem;color:var(--txt)} .step span{color:var(--mute)}
.arrow{color:var(--mute)}

/* links */
.link{display:flex;gap:12px;align-items:flex-start;background:var(--card2);border:1px solid var(--line);
      border-radius:14px;padding:10px 14px;margin-bottom:8px}
.risk{font-weight:800;font-size:.75rem;padding:4px 9px;border-radius:8px;white-space:nowrap}
.risk.HIGH{background:rgba(255,77,94,.18);color:var(--red)} .risk.MEDIUM{background:rgba(255,176,32,.18);color:var(--amber)}
.risk.LOW{background:rgba(46,229,157,.15);color:var(--green)}
.dom{font-family:ui-monospace,Menlo,monospace;color:var(--cyan);font-size:.92rem}
.why{color:var(--mute);font-size:.85rem;margin-top:2px}

/* explanation */
.explain{font-size:1.18rem;line-height:1.8;background:var(--card2);border:1px solid var(--line);
         border-left:4px solid var(--cyan);border-radius:14px;padding:16px 20px}
.cursor{display:inline-block;width:9px;height:1.1em;background:var(--cyan);vertical-align:text-bottom;animation:pulse 1s infinite}
.note{color:var(--mute);font-size:.82rem;margin-top:6px}

/* alerts */
.alert{background:var(--card2);border:1px solid var(--line);border-left:5px solid var(--red);border-radius:14px;
       padding:12px 16px;margin-bottom:10px}
.alert.warn{border-left-color:var(--amber)}
.alert .h{font-weight:800;letter-spacing:.04em} .alert .h small{color:var(--mute);font-weight:600;margin-left:8px}
.alert .d{margin:4px 0 6px}
.alert .w,.alert .t{color:var(--mute);font-size:.86rem} .alert .t b,.alert .w b{color:var(--txt)}
.allclear{background:rgba(46,229,157,.08);border:1px solid rgba(46,229,157,.35);color:var(--green);border-radius:14px;
          padding:12px 16px;font-weight:600}
</style>""", unsafe_allow_html=True)

SHIELD = """<svg width="54" height="62" viewBox="0 0 54 62"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#0e7490"/></linearGradient></defs>
<path d="M27 2 L51 11 V30 C51 45 40 55 27 60 C14 55 3 45 3 30 V11 Z" fill="url(#g)"/>
<path d="M17 31 l7 7 l13 -15" stroke="#03141a" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>"""


def esc(x):
    return html.escape(str(x))


def online():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=1).close()
        return True
    except OSError:
        return False


def cpu_temp():
    try:
        return int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000
    except Exception:
        return None


@st.cache_resource(show_spinner="Loading KAVACH models on the Arm CPU…")
def load():
    from kavach.pipeline import Kavach
    t = time.perf_counter()
    kv = Kavach(load_stage2=True)
    return kv, time.perf_counter() - t


k, load_s = load()
proc = psutil.Process(os.getpid())
fi = feed_info()

# ------------------------------------------------------------------ hero
net = online()
chips = [
    f"<span class='chip'><span class='dot {'a' if net else 'g'}'></span>"
    f"{'ONLINE — not used' if net else 'OFFLINE · 100% on-device'}</span>",
    f"<span class='chip'>🧩 Arm Cortex-A76 × {psutil.cpu_count()} · {esc(platform.machine())}</span>",
    f"<span class='chip'>🦙 {'Llama 3.2 1B · FP16' if k.stage2 else 'verified templates'}</span>",
]
if fi["urls"]:
    chips.append(f"<span class='chip'>🛡️ {fi['urls']} phishing links offline</span>")
st.markdown(
    f"<div class='hero'><div class='brand'>{SHIELD}<div><div class='name'>KAVACH</div>"
    f"<div class='tag'>On-device multilingual scam &amp; threat shield · Team Iconic · Bharat AI-SoC 2026-27 · PS3</div>"
    f"</div></div><div class='chips'>{''.join(chips)}</div></div>", unsafe_allow_html=True)
if k.stage2_error:
    st.caption(f"ℹ️ {k.stage2_error}")

tab_sms, tab_net = st.tabs(["📩  SMS & link shield", "🌐  Network shield"])

# ------------------------------------------------------------------ performance tiles
if "perf" not in st.session_state:
    st.session_state.perf = {"s1": None, "ttft": None, "tps": None}


def perf_html():
    p = st.session_state.perf
    ram = proc.memory_info().rss / 1e6
    cpu = psutil.cpu_percent(interval=None)
    t = cpu_temp()
    tcol = "var(--green)" if (t or 0) < 65 else "var(--amber)" if (t or 0) < 78 else "var(--red)"

    def tile(v, label, sub="", pct=None, col="var(--cyan)"):
        bar = f"<div class='bar'><i style='width:{max(2, min(100, pct)):.0f}%;background:{col}'></i></div>" if pct is not None else ""
        return f"<div class='tile'><div class='v'>{v}</div><div class='l'>{label}</div><div class='s'>{sub}</div>{bar}</div>"

    return "<div class='tiles'>" + "".join([
        tile(f"{p['s1']:.0f} ms" if p["s1"] is not None else "–", "Scam verdict", "IndicBERT INT8"),
        tile(f"{p['ttft']:.1f} s" if p["ttft"] is not None else "–", "First word", "Llama FP16"),
        tile(f"{p['tps']:.1f}" if p["tps"] is not None else "–", "Tokens / s", "on Cortex-A76"),
        tile(f"{ram / 1000:.1f} GB", "App RAM", "of 8 GB", ram / 80),
        tile(f"{cpu:.0f}%", "CPU", "4 cores", cpu),
        tile(f"{t:.0f}°C" if t else "–", "SoC temp", "BCM2712", (t or 0), tcol),
    ]) + "</div>"


# ------------------------------------------------------------------ SMS tab
with tab_sms:
    EXAMPLES = {
        "Tamil · KYC": "உங்கள் வங்கி கணக்கு இன்று முடக்கப்படும். உடனே KYC அப்டேட் செய்யுங்கள்: http://sbi-kyc-update.xyz",
        "Tanglish · OTP": "Ippo unga phone ku vandha OTP sollunga, thappa unga number ku vandhuduchu",
        "Hindi · power": "आपका बिजली कनेक्शन आज रात काट दिया जाएगा, तुरंत इस नंबर पर कॉल करें 9876543210",
        "Hinglish · army": "Main army officer hoon, aapka saman khareedna hai, pehle 1 rupaya bhejo confirm karne ke liye",
        "Bengali · family": "মা, আমার ফোন ভেঙে গেছে, এটা নতুন নম্বর। জরুরি ১০০০০ টাকা পাঠাও।",
        "Telugu · power": "మీ కరెంట్ కనెక్షన్ ఈరోజు రాత్రి కట్ చేయబడుతుంది, గత నెల బిల్ అప్‌డేట్ కాలేదు.",
        "English · bank ✓": "VM-SBIINB: Rs 1,200.00 debited from A/c XX7781 via UPI to SWIGGY. Not you? Call 1800 1234.",
        "Tamil · college ✓": "நாளைக்கு காலேஜ் லீவு, பரீட்சை திங்கள்கிழமை.",
    }

    if "history" not in st.session_state:
        st.session_state.history = []
    if "sms" not in st.session_state:
        st.session_state.sms = ""

    left, right = st.columns([3, 2], gap="large")

    with left:
        with st.container(key="panel_sms"):
            st.markdown("<div class='panel-title'>📩 Incoming SMS</div>", unsafe_allow_html=True)
            cols = st.columns(4)
            for i, (name, text) in enumerate(EXAMPLES.items()):
                if cols[i % 4].button(name, width='stretch'):
                    st.session_state.sms = text
            sms = st.text_area("Paste or type any SMS — Tamil, Tanglish, Hindi, Hinglish, Bengali, Telugu, English",
                               key="sms", height=110)
            go = st.button("🔍  Check with KAVACH", type="primary", width='stretch', disabled=not sms.strip())

    with right:
        with st.container(key="panel_perf"):
            st.markdown("<div class='panel-title'>⚙️ Live on the Arm SoC</div>", unsafe_allow_html=True)
            perf_box = st.empty()
            perf_box.markdown(perf_html(), unsafe_allow_html=True)
            st.markdown(f"<div class='note'>Models loaded in {load_s:.1f} s · Stage 1: IndicBERT INT8, vocab-pruned, "
                        f"38 MB · Stage 2: Llama 3.2 1B + LoRA, FP16 · ExecuTorch + XNNPACK · no cloud</div>",
                        unsafe_allow_html=True)

    if go and sms.strip():
        r = k.detect(sms)
        st.session_state.perf["s1"] = r["latency_ms"]
        perf_box.markdown(perf_html(), unsafe_allow_html=True)
        lang = LANG_NAMES.get(r["lang"], r["lang"])
        with left:
            scam = r["final"] == "SCAM"
            conf = r["p_scam"] if r["verdict"] == "SCAM" else 1 - r["p_scam"]
            sub = f"Confidence {conf * 100:.0f}% &nbsp;·&nbsp; Language: {esc(lang)}"
            if r.get("override"):
                sub += " &nbsp;·&nbsp; ⚠️ upgraded to SCAM because of a dangerous link"
            col = "var(--red)" if scam else "var(--green)"
            st.markdown(f"<div class='verdict {'scam' if scam else 'safe'}'>"
                        f"<div class='big'>{'🚨 SCAM' if scam else '✅ SAFE'}</div><div class='sub'>{sub}</div>"
                        f"<div class='conf'><i style='width:{conf * 100:.0f}%;background:{col}'></i></div></div>",
                        unsafe_allow_html=True)

            worst = max((l["risk"] for l in r["links"]), key=["LOW", "MEDIUM", "HIGH"].index) if r["links"] else "none"
            trace_box = st.empty()

            def trace(llm="…", check="…"):
                steps = [("Language", esc(lang)), ("IndicBERT INT8", f"{r['latency_ms']:.0f} ms"),
                         ("Link check", worst), ("Llama FP16", llm), ("Output check", check)]
                trace_box.markdown("<div class='trace'>" + "<span class='arrow'>›</span>".join(
                    f"<div class='step'><span>{a}</span><b>{b}</b></div>" for a, b in steps) + "</div>",
                    unsafe_allow_html=True)
            trace()

            if r["links"]:
                st.markdown("<div class='panel-title'>🔗 Link check</div>", unsafe_allow_html=True)
                for l in r["links"]:
                    st.markdown(f"<div class='link'><span class='risk {l['risk']}'>{l['risk']}</span><div>"
                                f"<div class='dom'>{esc(l['domain'])}</div>"
                                f"<div class='why'>{esc('; '.join(l['reasons']))}</div></div></div>",
                                unsafe_allow_html=True)

            st.markdown("<div class='panel-title'>🧠 KAVACH explains</div>", unsafe_allow_html=True)
            box = st.empty()
            info = {}
            for text, info in k.explain_stream(sms, r["final"], r["lang"]):
                body = esc(text).replace("\n", "<br>")
                box.markdown(f"<div class='explain'>{body}{'' if info.get('done') else '<span class=cursor></span>'}</div>",
                             unsafe_allow_html=True)
                if "ttft_s" in info:
                    st.session_state.perf["ttft"] = info["ttft_s"]
                    st.session_state.perf["tps"] = info.get("tok_s", 0)
                    perf_box.markdown(perf_html(), unsafe_allow_html=True)
                    trace(f"{info['ttft_s']:.1f} s first word")
            if info.get("source") == "fallback":
                trace("fallback", "verified message")
                st.markdown(f"<div class='note'>🛟 Showing a verified safety message (AI output check: "
                            f"{esc(info.get('reason'))}).</div>", unsafe_allow_html=True)
            else:
                ttft = st.session_state.perf["ttft"]
                trace(f"{ttft:.1f} s first word" if ttft is not None else "done", "passed ✓")
                st.markdown("<div class='note'>✔ AI explanation passed the output check · generated on-device</div>",
                            unsafe_allow_html=True)

        st.session_state.history.insert(0, {
            "time": time.strftime("%H:%M:%S"), "verdict": r["final"],
            "confidence": f"{(r['p_scam'] if r['verdict'] == 'SCAM' else 1 - r['p_scam']) * 100:.0f}%",
            "language": lang, "stage1_ms": round(r["latency_ms"]),
            "explained_by": "Llama" if info.get("source") == "llm" else "verified template",
            "sms": sms[:70]})

    if st.session_state.history:
        h = st.session_state.history
        st.markdown("<div class='panel-title' style='margin-top:18px'>📊 Session history</div>", unsafe_allow_html=True)
        st.markdown("<div class='tiles'>"
                    f"<div class='tile'><div class='v'>{len(h)}</div><div class='l'>Messages checked</div></div>"
                    f"<div class='tile'><div class='v' style='color:var(--red)'>{sum(x['verdict'] == 'SCAM' for x in h)}</div>"
                    f"<div class='l'>Scams caught</div></div>"
                    f"<div class='tile'><div class='v'>{sum(x['stage1_ms'] for x in h) / len(h):.0f} ms</div>"
                    f"<div class='l'>Avg verdict time</div></div></div>", unsafe_allow_html=True)
        st.write("")
        st.dataframe(h, width='stretch', hide_index=True)


# ------------------------------------------------------------------ Network tab
@st.cache_resource
def netmon():
    from kavach.netmon import NetMonitor
    return NetMonitor(interval=1.0, warmup=30).start()


@st.cache_resource
def devwatch():
    from kavach.netdevices import DeviceWatch
    return DeviceWatch(interval=5, sweep_every=20)


def alert_card(time_, kind, detail, why, todo, warn=False):
    return (f"<div class='alert {'warn' if warn else ''}'><div class='h'>{'⚠️' if warn else '🚨'} {esc(kind)}"
            f"<small>{esc(time_)}</small></div><div class='d'>{esc(detail)}</div>"
            f"<div class='w'><b>Why it matters:</b> {esc(why)}</div><div class='t'><b>What to do:</b> {esc(todo)}</div></div>")


with tab_net:
    mon = netmon()
    dw = devwatch()

    @st.fragment(run_every=2)
    def live():
        s = mon.status()
        status = (f"Learning · {s['warmup_left']} s" if s["learning"] else "Monitoring")
        st.markdown("<div class='tiles' style='grid-template-columns:repeat(4,1fr)'>"
                    f"<div class='tile'><div class='v'><span class='dot {'a' if s['learning'] else 'g'}'></span> "
                    f"{status}</div><div class='l'>Shield status</div></div>"
                    f"<div class='tile'><div class='v'>{s['upload_kBps']:,.0f}</div><div class='l'>Upload kB/s</div></div>"
                    f"<div class='tile'><div class='v'>{s['download_kBps']:,.0f}</div><div class='l'>Download kB/s</div></div>"
                    f"<div class='tile'><div class='v'>{s['active_conns']}</div><div class='l'>Active connections</div></div>"
                    "</div>", unsafe_allow_html=True)
        h = s["history"][-60:]
        if h:
            st.area_chart({"upload kB/s": [x[1] / 1e3 for x in h], "download kB/s": [x[2] / 1e3 for x in h]},
                          height=170, color=["#22d3ee", "#ff4d5e"])
        if s["alerts"]:
            st.markdown("".join(alert_card(a["time"], a["type"].replace("_", " "), a["detail"], a["why"],
                                           a["what_to_do"], warn=a["severity"] != "HIGH")
                                for a in s["alerts"][:8]), unsafe_allow_html=True)
        else:
            st.markdown("<div class='allclear'>✔ No network threats detected</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        with st.container(key="panel_net"):
            st.markdown("<div class='panel-title'>🌐 Traffic & intrusion watch · this device</div>"
                        "<div class='note' style='margin:-4px 0 10px'>Learns normal for 30 s, then flags port scans, "
                        "data-theft bursts, connection floods, malware ports and new backdoor listeners.</div>",
                        unsafe_allow_html=True)
            live()

    with c2:
        with st.container(key="panel_dev"):
            st.markdown("<div class='panel-title'>📡 Devices on your Wi-Fi · IoT watch</div>"
                        "<div class='note' style='margin:-4px 0 10px'>Hears the DHCP “I just joined” broadcast instantly, "
                        "and asks the network who is there every 20 s (ARP). No packet capture, no internet.</div>",
                        unsafe_allow_html=True)

            @st.fragment(run_every=5)
            def devices():
                s = dw.snapshot()
                on = s["dhcp"] == "on"
                st.markdown("<div class='tiles'>"
                            f"<div class='tile'><div class='v'>{s['active']}<span style='font-size:1rem;color:var(--mute)'>"
                            f" / {len(s['devices'])}</span></div><div class='l'>Active / seen</div></div>"
                            f"<div class='tile'><div class='v'><span class='dot {'g' if s['ready'] else 'a'}'></span> "
                            f"{'Watching' if s['ready'] else 'Learning'}</div><div class='l'>Status</div></div>"
                            f"<div class='tile'><div class='v'><span class='dot {'g' if on else 'a'}'></span> "
                            f"{'On' if on else 'Off'}</div><div class='l'>DHCP sensor</div>"
                            f"<div class='s'>{s['dhcp_events']} join packets</div></div></div>",
                            unsafe_allow_html=True)
                if not on:
                    st.caption(f"DHCP join sensor: {s['dhcp']}")
                st.write("")
                if s["alerts"]:
                    st.markdown("".join(alert_card(a["time"], "NEW DEVICE", a["detail"], a["why"], a["todo"], warn=True)
                                        for a in s["alerts"][:4]), unsafe_allow_html=True)
                if s["devices"]:
                    st.dataframe([{"": "🆕" if s["ready"] and d["mac"] not in dw.baseline else "",
                                   "name": d["name"] or "—", "IP": d["ip"], "maker": d["maker"],
                                   "found by": d["via"].upper(), "status": d["state"], "first seen": d["first_seen"],
                                   "MAC": d["mac"]}
                                  for d in sorted(s["devices"], key=lambda x: x["ip"])],
                                 width='stretch', hide_index=True)
            devices()
