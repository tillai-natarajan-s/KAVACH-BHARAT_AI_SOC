"""Network anomaly detection — runs fully on-device (Raspberry Pi 5), no cloud, no packet capture library needed.

Every second it samples the device's network counters and open connections, learns a baseline for the first
~30 s, then raises plain-language alerts for:
  TRAFFIC_SPIKE    sudden upload/download burst far above normal (possible data theft / malware download)
  PORT_SCAN        one address touching many different ports in a short time (someone probing the device)
  CONN_SURGE       far more open connections than normal (botnet / flooding)
  SUSPICIOUS_PORT  connection to a port typically used by malware / remote-control tools
  NEW_LISTENER     a program started accepting connections from outside after the baseline
"""
import collections
import statistics
import threading
import time

import psutil

SUSPICIOUS_PORTS = {23: "Telnet (insecure remote login, used by IoT botnets like Mirai)",
                    2323: "alternate Telnet (IoT botnets)",
                    4444: "Metasploit / reverse-shell default",
                    5555: "Android debug bridge (remote takeover)",
                    6667: "IRC (botnet command channel)",
                    1337: "common backdoor port", 31337: "classic backdoor port",
                    3389: "remote desktop", 5900: "VNC remote screen"}

ADVICE = {
    "TRAFFIC_SPIKE": ("Unusual burst of data leaving or entering this device.",
                      "Disconnect unknown devices from Wi-Fi, check which app is uploading, change the Wi-Fi password."),
    "PORT_SCAN": ("Someone on the network is probing many ports on this device — the first step of an attack.",
                  "Block that address on the router, make sure the router firmware is updated, turn off unused services."),
    "CONN_SURGE": ("Far more network connections than normal — possible malware, botnet activity or flooding.",
                   "Restart the device, check recently installed apps, and scan the network for unknown devices."),
    "SUSPICIOUS_PORT": ("A connection uses a port commonly used by malware or remote-control tools.",
                        "Stop the program using it, change default passwords on cameras/IoT devices, disable Telnet."),
    "NEW_LISTENER": ("A program on this device started accepting connections from outside.",
                     "Check which program opened the port; if you don't recognise it, stop it and remove it."),
}


def tcp_counters():
    """Linux kernel TCP counters. A port scan against closed ports leaves no open connection, but the kernel
    answers every probe with a reset (OutRsts) — so a burst of resets is the scan's fingerprint."""
    try:
        lines = [l.split() for l in open("/proc/net/snmp") if l.startswith("Tcp:")]
        return dict(zip(lines[0][1:], map(int, lines[1][1:])))
    except Exception:
        return {}


class NetMonitor:
    def __init__(self, interval=1.0, warmup=30, window=120):
        self.interval, self.warmup = interval, warmup
        self.hist = collections.deque(maxlen=window)          # (t, sent_Bps, recv_Bps, n_conns)
        self.alerts = collections.deque(maxlen=200)
        self.port_hits = collections.defaultdict(dict)         # remote ip -> {port: last_seen}
        self.listeners = None
        self.samples = 0
        self._last_alert = {}
        self._prev = None
        self._stop = threading.Event()
        self._thread = None

    # ---------- sampling ----------
    def _conns(self):
        try:
            return psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            return []

    def _alert(self, kind, severity, detail, key=None, cooldown=15):
        key = key or kind
        now = time.time()
        if now - self._last_alert.get(key, 0) < cooldown:
            return
        self._last_alert[key] = now
        why, todo = ADVICE[kind]
        self.alerts.appendleft({"time": time.strftime("%H:%M:%S"), "type": kind, "severity": severity,
                                "detail": detail, "why": why, "what_to_do": todo})

    def sample(self):
        now = time.time()
        io = psutil.net_io_counters()
        conns = self._conns()
        tcp = tcp_counters()
        if self._prev is None:
            self._prev = (now, io.bytes_sent, io.bytes_recv)
            self._prev_tcp = tcp
            return
        rst_rate = (tcp.get("OutRsts", 0) - self._prev_tcp.get("OutRsts", 0)) / max(now - self._prev[0], 1e-3)
        fail_rate = (tcp.get("AttemptFails", 0) - self._prev_tcp.get("AttemptFails", 0)) / max(now - self._prev[0], 1e-3)
        self._prev_tcp = tcp
        dt = max(now - self._prev[0], 1e-3)
        sent = (io.bytes_sent - self._prev[1]) / dt
        recv = (io.bytes_recv - self._prev[2]) / dt
        self._prev = (now, io.bytes_sent, io.bytes_recv)
        active = [c for c in conns if c.status in ("ESTABLISHED", "SYN_SENT", "SYN_RECV")]
        self.samples += 1

        # port-scan tracking: distinct ports each remote address touched in the last 10 s
        for c in conns:
            if c.raddr and c.laddr:
                ip = c.raddr.ip
                local_port = c.laddr.port
                remote_port = c.raddr.port
                # inbound probe: remote -> many of OUR ports; outbound scan: us -> many ports of THEIR host
                self.port_hits[("in", ip)][local_port] = now
                self.port_hits[("out", ip)][remote_port] = now
        for key in list(self.port_hits):
            ports = {p: t for p, t in self.port_hits[key].items() if now - t < 10}
            self.port_hits[key] = ports
            if not ports:
                del self.port_hits[key]

        learning = self.samples <= self.warmup
        if not learning and len(self.hist) >= 10:
            base = list(self.hist)[:-1]
            for name, val, idx, floor in (("upload", sent, 1, 1_000_000), ("download", recv, 2, 5_000_000)):
                xs = [h[idx] for h in base]
                mu, sd = statistics.mean(xs), statistics.pstdev(xs) or 1.0
                if val > floor and val > mu + 4 * sd:
                    self._alert("TRAFFIC_SPIKE", "HIGH",
                                f"{name} {val / 1e6:.1f} MB/s vs normal {mu / 1e6:.2f} MB/s", key=f"spike-{name}")
            ns = [h[3] for h in base]
            mu, sd = statistics.mean(ns), statistics.pstdev(ns) or 1.0
            if len(active) > max(50, mu + 4 * sd):
                self._alert("CONN_SURGE", "MEDIUM", f"{len(active)} active connections vs normal {mu:.0f}")

        if not learning and rst_rate >= 15:
            self._alert("PORT_SCAN", "HIGH", f"{rst_rate:.0f} connection attempts per second hit closed ports on this "
                        f"device (kernel reset counter)", key="scan-rst")
        if not learning and fail_rate >= 15:
            self._alert("PORT_SCAN", "HIGH", f"this device made {fail_rate:.0f} failed connection attempts per second "
                        f"(possible infected program scanning the network)", key="scan-fail")
        for (direction, ip), ports in self.port_hits.items():
            if len(ports) >= 15:
                who = f"{ip} probed {len(ports)} ports on this device" if direction == "in" \
                    else f"this device contacted {len(ports)} different ports on {ip}"
                self._alert("PORT_SCAN", "HIGH", who + " within 10 s", key=f"scan-{direction}-{ip}")

        for c in active:
            if c.raddr and c.raddr.port in SUSPICIOUS_PORTS:
                self._alert("SUSPICIOUS_PORT", "HIGH",
                            f"{c.raddr.ip}:{c.raddr.port} — {SUSPICIOUS_PORTS[c.raddr.port]}",
                            key=f"port-{c.raddr.ip}-{c.raddr.port}")

        listen = {c.laddr.port for c in conns if c.status == "LISTEN" and c.laddr
                  and c.laddr.ip not in ("127.0.0.1", "::1")}
        if learning or self.listeners is None:
            self.listeners = (self.listeners or set()) | listen
        else:
            for p in listen - self.listeners:
                extra = f" ({SUSPICIOUS_PORTS[p]})" if p in SUSPICIOUS_PORTS else ""
                self._alert("NEW_LISTENER", "HIGH" if p in SUSPICIOUS_PORTS else "MEDIUM",
                            f"new open port {p}{extra}", key=f"listen-{p}")
            self.listeners |= listen

        self.hist.append((now, sent, recv, len(active)))

    # ---------- background thread ----------
    def _loop(self):
        while not self._stop.is_set():
            t0 = time.time()
            try:
                self.sample()
            except Exception:
                pass
            self._stop.wait(max(0.0, self.interval - (time.time() - t0)))

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        return self

    def stop(self):
        self._stop.set()

    def status(self):
        h = list(self.hist)
        last = h[-1] if h else (0, 0, 0, 0)
        return {"learning": self.samples <= self.warmup, "warmup_left": max(0, self.warmup - self.samples),
                "upload_kBps": last[1] / 1e3, "download_kBps": last[2] / 1e3, "active_conns": last[3],
                "history": h, "alerts": list(self.alerts)}
