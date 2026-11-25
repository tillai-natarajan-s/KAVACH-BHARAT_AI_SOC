"""KAVACH dashboard — run with:  streamlit run app.py"""
import os, platform, socket, time
import psutil
import streamlit as st

from kavach import config
from kavach.lang import LANG_NAMES
from kavach.urlcheck import feed_info

st.set_page_config(page_title="KAVACH", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.verdict {border-radius:14px;padding:18px 22px;margin:6px 0 14px 0;color:#fff}
.verdict h1 {margin:0;font-size:2.4rem}
.scam {background:linear-gradient(135deg,#b3001b,#e5383b)}
.safe {background:linear-gradient(135deg,#1b7a3d,#2fbf71)}
.badge {display:inline-block;padding:4px 12px;border-radius:999px;font-weight:600;margin-right:8px;font-size:.85rem}
.off {background:#1b7a3d;color:#fff} .on {background:#e08e0b;color:#fff} .dev {background:#334;color:#fff}
.explain {font-size:1.15rem;line-height:1.7;background:rgba(127,127,127,.08);border-radius:12px;padding:14px 18px}
.link-high {color:#e5383b;font-weight:700} .link-med {color:#e08e0b;font-weight:700} .link-low {color:#2fbf71;font-weight:700}
</style>""", unsafe_allow_html=True)


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


@st.cache_resource(show_spinner="Loading KAVACH models on device…")
def load():
    from kavach.pipeline import Kavach
    t = time.perf_counter()
    k = Kavach(load_stage2=True)
    return k, time.perf_counter() - t


k, load_s = load()
proc = psutil.Process(os.getpid())

# ---------- header ----------
net = online()
st.markdown(
    f"<h1 style='margin-bottom:0'>🛡️ KAVACH</h1>"
    f"<div style='opacity:.75;margin-bottom:8px'>On-device multilingual scam shield · Team Iconic · Bharat AI-SoC 2026-27 (PS3)</div>"
    f"<span class='badge {'on' if net else 'off'}'>{'🌐 ONLINE (not used)' if net else '✈️ OFFLINE — 100% on-device'}</span>"
    f"<span class='badge dev'>💻 {platform.machine()} · {psutil.cpu_count()} cores</span>"
    f"<span class='badge dev'>Stage 2: {'Llama 3.2 1B (fine-tuned)' if k.stage2 else 'verified templates'}</span>",
    unsafe_allow_html=True)
if k.stage2_error:
    st.caption(f"ℹ️ {k.stage2_error}")

tab_sms, tab_net = st.tabs(["📩 SMS & link shield", "🌐 Network shield"])

with tab_sms:

    EXAMPLES = {
        "Tamil – bank KYC": "உங்கள் வங்கி கணக்கு இன்று முடக்கப்படும். உடனே KYC அப்டேட் செய்யுங்கள்: http://sbi-kyc-update.xyz",
        "Tanglish – OTP": "Ippo unga phone ku vandha OTP sollunga, thappa unga number ku vandhuduchu",
        "Hindi – electricity": "आपका बिजली कनेक्शन आज रात काट दिया जाएगा, तुरंत इस नंबर पर कॉल करें 9876543210",
        "Hinglish – army buyer": "Main army officer hoon, aapka saman khareedna hai, pehle 1 rupaya bhejo confirm karne ke liye",
        "Bengali – new number": "মা, আমার ফোন ভেঙে গেছে, এটা নতুন নম্বর। জরুরি ১০০০০ টাকা পাঠাও।",
        "Telugu – power cut": "మీ కరెంట్ కనెక్షన్ ఈరోజు రాత్రి కట్ చేయబడుతుంది, గత నెల బిల్ అప్‌డేట్ కాలేదు.",
        "English – genuine debit": "VM-SBIINB: Rs 1,200.00 debited from A/c XX7781 via UPI to SWIGGY. Not you? Call 1800 1234.",
        "Tamil – genuine": "நாளைக்கு காலேஜ் லீவு, பரீட்சை திங்கள்கிழமை.",
    }

    if "history" not in st.session_state:
        st.session_state.history = []
    if "sms" not in st.session_state:
        st.session_state.sms = ""

    left, right = st.columns([3, 2], gap="large")

    with left:
        st.subheader("📩 Incoming SMS")
        cols = st.columns(4)
        for i, (name, text) in enumerate(EXAMPLES.items()):
            if cols[i % 4].button(name, width='stretch'):
                st.session_state.sms = text
        sms = st.text_area("Paste or type any SMS (Tamil, Tanglish, Hindi, Hinglish, Bengali, Telugu, English)",
                           key="sms", height=110)
        go = st.button("🔍 Check with KAVACH", type="primary", width='stretch', disabled=not sms.strip())
        fi = feed_info()
        if fi["urls"]:
            st.caption(f"🛡️ Offline threat feed: {fi['urls']} known phishing links ({fi['source']}, saved {fi['date']}) "
                       f"+ look-alike rules — link checks need no internet.")

    with right:
        st.subheader("⚙️ On-device performance (Arm)")
        m1, m2, m3 = st.columns(3)
        s1_box, ttft_box, tps_box = m1.empty(), m2.empty(), m3.empty()
        m4, m5, m6 = st.columns(3)
        ram_box, cpu_box, tmp_box = m4.empty(), m5.empty(), m6.empty()

        def show_sys():
            ram_box.metric("App RAM", f"{proc.memory_info().rss / 1e6:,.0f} MB")
            cpu_box.metric("CPU", f"{psutil.cpu_percent(interval=None):.0f} %")
            t = cpu_temp()
            tmp_box.metric("SoC temp", f"{t:.0f} °C" if t else "–")

        s1_box.metric("Stage 1 detect", "–")
        ttft_box.metric("Stage 2 first word", "–")
        tps_box.metric("Stage 2 speed", "–")
        show_sys()
        st.caption(f"Models loaded in {load_s:.1f} s · Stage 1: IndicBERT INT8 + vocab-pruned (37.5 MB, ExecuTorch/XNNPACK) · "
                   f"Stage 2: Llama 3.2 1B LoRA, FP16 (ExecuTorch/XNNPACK)")

    if go and sms.strip():
        r = k.detect(sms)
        s1_box.metric("Stage 1 detect", f"{r['latency_ms']:.0f} ms")
        with left:
            scam = r["final"] == "SCAM"
            conf = r["p_scam"] if r["verdict"] == "SCAM" else 1 - r["p_scam"]
            sub = f"Stage 1 confidence {conf * 100:.0f}% · language: {LANG_NAMES.get(r['lang'], r['lang'])}"
            if r.get("override"):
                sub += " · upgraded to SCAM because of a dangerous link"
            st.markdown(f"<div class='verdict {'scam' if scam else 'safe'}'><h1>{'🚨 SCAM' if scam else '✅ SAFE'}</h1>"
                        f"<div>{sub}</div></div>", unsafe_allow_html=True)

            if r["links"]:
                st.markdown("**🔗 Link check**")
                for l in r["links"]:
                    cls = {"HIGH": "link-high", "MEDIUM": "link-med", "LOW": "link-low"}[l["risk"]]
                    st.markdown(f"<span class='{cls}'>{l['risk']}</span> `{l['domain']}` — {'; '.join(l['reasons'])}",
                                unsafe_allow_html=True)

            st.markdown("**🧠 KAVACH explains**")
            box = st.empty()
            info = {}
            for text, info in k.explain_stream(sms, r["final"], r["lang"]):
                box.markdown(f"<div class='explain'>{text.replace(chr(10), '<br>')}▌</div>"
                             if not info.get("done") else
                             f"<div class='explain'>{text.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
                if "ttft_s" in info:
                    ttft_box.metric("Stage 2 first word", f"{info['ttft_s']:.1f} s")
                    tps_box.metric("Stage 2 speed", f"{info.get('tok_s', 0):.1f} tok/s")
                    show_sys()
            if info.get("source") == "fallback":
                st.caption(f"🛟 Showing a verified safety message (AI output check: {info.get('reason')}).")
            else:
                st.caption("✔️ AI explanation passed the output check.")

        st.session_state.history.insert(0, {
            "time": time.strftime("%H:%M:%S"), "verdict": r["final"],
            "confidence": f"{(r['p_scam'] if r['verdict'] == 'SCAM' else 1 - r['p_scam']) * 100:.0f}%",
            "language": LANG_NAMES.get(r["lang"], r["lang"]), "stage1_ms": round(r["latency_ms"]),
            "explained_by": "Llama" if info.get("source") == "llm" else "verified template",
            "sms": sms[:70]})

    if st.session_state.history:
        st.divider()
        h = st.session_state.history
        c1, c2, c3 = st.columns(3)
        c1.metric("Messages checked", len(h))
        c2.metric("Scams caught", sum(x["verdict"] == "SCAM" for x in h))
        c3.metric("Avg Stage 1", f"{sum(x['stage1_ms'] for x in h) / len(h):.0f} ms")
        st.dataframe(h, width='stretch', hide_index=True)


# ---------------- Network shield ----------------
@st.cache_resource
def netmon():
    from kavach.netmon import NetMonitor
    return NetMonitor(interval=1.0, warmup=30).start()


@st.cache_resource
def devwatch():
    from kavach.netdevices import DeviceWatch
    return DeviceWatch(interval=5, sweep_every=20)


with tab_net:
    st.subheader("🌐 Home-network anomaly detection (on-device)")
    st.caption("Watches this device's traffic and connections every second, learns what is normal for 30 s, then "
               "flags port scans, data-theft bursts, connection floods, malware ports and new backdoor listeners.")
    mon = netmon()

    @st.fragment(run_every=2)
    def live():
        s = mon.status()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Status", f"Learning… {s['warmup_left']} s" if s["learning"] else "🟢 Monitoring")
        c2.metric("Upload", f"{s['upload_kBps']:,.0f} kB/s")
        c3.metric("Download", f"{s['download_kBps']:,.0f} kB/s")
        c4.metric("Active connections", s["active_conns"])
        h = s["history"][-60:]
        if h:
            st.line_chart({"upload kB/s": [x[1] / 1e3 for x in h], "download kB/s": [x[2] / 1e3 for x in h]},
                          height=180)
        if s["alerts"]:
            for a in s["alerts"][:8]:
                icon = "🚨" if a["severity"] == "HIGH" else "⚠️"
                st.markdown(f"<div class='verdict {'scam' if a['severity'] == 'HIGH' else 'safe'}' "
                            f"style='padding:10px 16px;{'' if a['severity'] == 'HIGH' else 'background:#b36b00'}'>"
                            f"<b>{icon} {a['time']} · {a['type'].replace('_', ' ')}</b><br>{a['detail']}<br>"
                            f"<span style='opacity:.9'>Why it matters: {a['why']}</span><br>"
                            f"<span style='opacity:.9'>What to do: {a['what_to_do']}</span></div>",
                            unsafe_allow_html=True)
        else:
            st.success("No network threats detected.")
    live()

    st.divider()
    st.subheader("📡 Devices on your Wi-Fi (IoT watch)")
    st.caption("Two offline sensors: (1) listens for the DHCP 'I just joined' broadcast every device sends when it "
               "connects — catches it instantly; (2) every 20 s asks the network who is there (ARP). "
               "Devices present at start are the baseline; any new device after that raises an alert.")
    dw = devwatch()

    @st.fragment(run_every=5)
    def devices():
        s = dw.snapshot()
        c1, c2, c3 = st.columns(3)
        c1.metric("Devices active now", f"{s['active']} of {len(s['devices'])} seen")
        c2.metric("Status", "🟢 Watching" if s["ready"] else "Learning who is normal…")
        c3.metric("DHCP join sensor", "🟢 on" if s["dhcp"] == "on" else "⚪ off", f"{s['dhcp_events']} join packets heard",
                  delta_color="off")
        if s["dhcp"] != "on":
            st.caption(f"DHCP join sensor: {s['dhcp']}")
        for a in s["alerts"][:5]:
            st.markdown(f"<div class='verdict' style='padding:10px 16px;background:#b36b00'>"
                        f"<b>⚠️ {a['time']} · NEW DEVICE</b><br>{a['detail']}<br>"
                        f"<span style='opacity:.9'>Why it matters: {a['why']}</span><br>"
                        f"<span style='opacity:.9'>What to do: {a['todo']}</span></div>", unsafe_allow_html=True)
        if s["devices"]:
            st.dataframe([{"IP": d["ip"], "name": d["name"], "MAC": d["mac"], "maker": d["maker"],
                           "found by": d["via"].upper(), "status": d["state"],
                           "first seen": d["first_seen"],
                           "new?": "🆕" if s["ready"] and d["mac"] not in dw.baseline else ""}
                          for d in sorted(s["devices"], key=lambda x: x["ip"])],
                         width='stretch', hide_index=True)
    devices()
