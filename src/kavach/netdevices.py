"""Home-network device watch (IoT / unknown-device alert). Fully offline, no root, no packet capture.
Reads the kernel neighbour (ARP) table with `ip neigh` every few seconds. Devices seen during the first
scan are the baseline; any NEW device (new MAC address) that appears later raises an alert."""
import ipaddress
import re
import socket
import subprocess
import threading
import time

# First 3 bytes of a MAC = maker (OUI). Small offline list of common makers in Indian homes.
OUI = {"b8:27:eb": "Raspberry Pi", "dc:a6:32": "Raspberry Pi", "d8:3a:dd": "Raspberry Pi", "2c:cf:67": "Raspberry Pi",
       "e4:5f:01": "Raspberry Pi", "24:0a:c4": "Espressif (IoT)", "30:ae:a4": "Espressif (IoT)",
       "a4:cf:12": "Espressif (IoT)", "84:f3:eb": "Espressif (IoT)", "ec:fa:bc": "Espressif (IoT)",
       "50:c7:bf": "TP-Link", "ac:84:c6": "TP-Link", "f4:f2:6d": "TP-Link", "c0:25:e9": "TP-Link",
       "00:1a:11": "Google", "f4:f5:d8": "Google", "44:07:0b": "Google", "fc:65:de": "Amazon (Echo/Fire)",
       "68:37:e9": "Amazon (Echo/Fire)", "00:17:88": "Philips Hue", "b0:4e:26": "TP-Link", "d0:73:d5": "LIFX",
       "a0:d3:c1": "Hewlett Packard", "3c:5a:b4": "Google", "18:b4:30": "Nest", "64:16:66": "Nest",
       "00:0e:58": "Sonos", "b4:79:a7": "Samsung", "8c:79:f5": "Samsung", "f0:18:98": "Apple",
       "3c:22:fb": "Apple", "a4:83:e7": "Apple", "9c:28:f7": "Xiaomi", "64:09:80": "Xiaomi", "28:6c:07": "Xiaomi",
       "c8:3a:35": "Tenda", "e8:4e:06": "Tenda", "00:e0:4c": "Realtek", "fc:ec:da": "Ubiquiti"}

LINE_RE = re.compile(r"^(\S+) dev (\S+)(?: lladdr ([0-9a-f:]{17}))?.*?(REACHABLE|STALE|DELAY|PROBE|PERMANENT|FAILED|INCOMPLETE|NOARP)?\s*$", re.I)


def _maker(mac):
    if not mac:
        return "unknown"
    if int(mac.split(":")[0], 16) & 2:
        return "randomised MAC (phone privacy mode)"
    return OUI.get(mac[:8].lower(), "unknown maker")


def _subnets():
    """IPv4 subnets of this device's network interfaces (wlan0 / eth0), from `ip -4 -o addr`."""
    nets = []
    try:
        out = subprocess.run(["ip", "-4", "-o", "addr", "show"], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return nets
    for line in out.split("\n"):
        m = re.search(r"^\d+:\s+(\S+)\s+inet\s+(\d+\.\d+\.\d+\.\d+/\d+)", line)
        if m and m.group(1) != "lo":
            net = ipaddress.ip_network(m.group(2), strict=False)
            if net.prefixlen < 22:                         # cap the sweep at 1024 addresses
                net = ipaddress.ip_network(f"{m.group(2).split('/')[0]}/22", strict=False)
            nets.append(net)
    return nets


def sweep():
    """Touch every address on the local subnet with one tiny UDP packet (port 9, 'discard').
    The kernel must ARP for each address, so every live device lands in the neighbour table.
    No root, no packet capture, ~1 KB of traffic per 254 hosts."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setblocking(False)
    for net in _subnets():
        for ip in net.hosts():
            try:
                s.sendto(b"\0", (str(ip), 9))
            except OSError:
                pass
    s.close()


def scan():
    """Current devices on the LAN: {mac: {ip, iface, state, maker}}."""
    try:
        out = subprocess.run(["ip", "neigh"], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return {}
    devs = {}
    for line in out.splitlines():
        m = LINE_RE.match(line.strip())
        if not m or not m.group(3):
            continue
        ip, iface, mac, state = m.group(1), m.group(2), m.group(3).lower(), (m.group(4) or "").upper()
        if ":" in ip and ip.lower().startswith("fe80"):
            continue                       # skip IPv6 link-local duplicates
        if state in ("FAILED", "INCOMPLETE"):
            continue
        d = devs.setdefault(mac, {"ip": ip, "iface": iface, "state": state, "maker": _maker(mac)})
        if "." in ip:
            d["ip"] = ip
    return devs


DHCP_TYPES = {1: "DISCOVER", 3: "REQUEST", 4: "DECLINE", 7: "RELEASE", 8: "INFORM"}


def parse_dhcp(pkt):
    """Parse a DHCP client packet (BOOTREQUEST). Returns {mac, type, hostname, vendor, ip} or None."""
    if len(pkt) < 240 or pkt[0] != 1 or pkt[236:240] != b"\x63\x82\x53\x63":
        return None
    mac = ":".join(f"{b:02x}" for b in pkt[28:34])
    info = {"mac": mac, "type": None, "hostname": "", "vendor": "", "ip": ""}
    ciaddr = ".".join(str(b) for b in pkt[12:16])
    if ciaddr != "0.0.0.0":
        info["ip"] = ciaddr
    i = 240
    while i < len(pkt):
        code = pkt[i]
        if code == 255:
            break
        if code == 0:
            i += 1
            continue
        if i + 1 >= len(pkt):
            break
        ln = pkt[i + 1]
        val = pkt[i + 2:i + 2 + ln]
        if code == 53 and ln >= 1:
            info["type"] = DHCP_TYPES.get(val[0], str(val[0]))
        elif code == 12:
            info["hostname"] = val.decode("utf-8", "ignore")
        elif code == 60:
            info["vendor"] = val.decode("utf-8", "ignore")
        elif code == 50 and ln == 4:
            info["ip"] = ".".join(str(b) for b in val)
        i += 2 + ln
    return info


def open_dhcp_socket():
    """Listen for DHCP broadcasts on UDP 67. A joining device broadcasts DISCOVER/REQUEST to everyone,
    so the Pi hears it the moment the device connects. Port 67 needs CAP_NET_BIND_SERVICE (see README)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(("", 67))
    s.settimeout(1.0)
    return s


def _own_macs():
    macs = set()
    try:
        import glob
        for f in glob.glob("/sys/class/net/*/address"):
            macs.add(open(f).read().strip().lower())
    except Exception:
        pass
    return macs


class DeviceWatch:
    """Background thread. .devices = current table, .alerts = list of new-device alerts (newest first)."""

    def __init__(self, interval=5, sweep_every=20):
        self.interval = interval
        self.sweep_every = sweep_every
        self._last_sweep = 0
        self.baseline = set()
        self.known = {}
        self.devices = {}
        self.alerts = []
        self.started = time.time()
        self.ready = False
        self._lock = threading.Lock()
        self.own = _own_macs()
        self.dhcp_status = "starting"
        self.dhcp_events = 0
        threading.Thread(target=self._loop, daemon=True).start()
        threading.Thread(target=self._dhcp_loop, daemon=True).start()

    def _add(self, mac, ip, maker, via, name=""):
        """Record a device; raise NEW_DEVICE if it was not there at baseline. Caller holds the lock."""
        now = time.time()
        if mac in self.own:
            return
        if mac not in self.known:
            self.known[mac] = {"ip": ip or "?", "iface": "", "state": "", "maker": maker,
                               "first_seen": time.strftime("%H:%M:%S"), "name": name, "via": via}
            if self.ready:
                who = f"'{name}' " if name else ""
                self.alerts.insert(0, {
                    "time": self.known[mac]["first_seen"], "type": "NEW_DEVICE",
                    "detail": f"new device {who}{ip or ''} ({mac}, {maker}) joined the network"
                              f" — seen via {'DHCP join broadcast (instant)' if via == 'dhcp' else 'ARP scan'}",
                    "why": "An unknown device on your Wi-Fi can spy on traffic or attack other devices; "
                           "cheap IoT gadgets are a common entry point.",
                    "todo": "Check whether you recognise it. If not: change the Wi-Fi password, "
                            "block its MAC on the router, keep IoT devices on a guest network."})
        d = self.known[mac]
        if ip:
            d["ip"] = ip
        if name and not d.get("name"):
            d["name"] = name
        d["last_seen"] = time.strftime("%H:%M:%S")
        d["_t"] = now

    def _dhcp_loop(self):
        try:
            sock = open_dhcp_socket()
            self.dhcp_status = "on"
        except PermissionError:
            self.dhcp_status = "off — needs permission (run the setcap command in README_RUN.md)"
            return
        except OSError as e:
            self.dhcp_status = f"off — {e}"
            return
        while True:
            try:
                pkt, _ = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                continue
            info = parse_dhcp(pkt)
            if not info or info["type"] not in ("DISCOVER", "REQUEST", "INFORM"):
                continue
            with self._lock:
                self.dhcp_events += 1
                maker = _maker(info["mac"])
                if info["vendor"]:
                    maker = f"{maker} · {info['vendor']}"
                self._add(info["mac"], info["ip"], maker, "dhcp", info["hostname"])

    def _loop(self):
        while True:
            if time.time() - self._last_sweep >= self.sweep_every:
                sweep()
                self._last_sweep = time.time()
                time.sleep(2)                      # give ARP replies time to arrive
            cur = scan()
            now = time.time()
            with self._lock:
                for mac, d in cur.items():
                    self._add(mac, d["ip"], d["maker"], "arp")
                    if mac in self.known:
                        self.known[mac]["state"] = d["state"]
                # keep every device ever seen; phones that go quiet are shown as "idle", not removed
                self.devices = dict(self.known)
                if not self.ready and now - self.started >= 3 * self.interval:
                    self.baseline = set(self.known)
                    self.ready = True
            time.sleep(self.interval)

    def snapshot(self):
        with self._lock:
            now = time.time()
            devs = []
            for m, d in list(self.known.items()):
                active = now - d.get("_t", 0) <= 60
                devs.append({"mac": m, "ip": d["ip"], "maker": d["maker"], "name": d.get("name", ""),
                             "via": d.get("via", ""), "first_seen": d.get("first_seen", ""),
                             "last_seen": d.get("last_seen", ""), "active": active,
                             "state": "active" if active else f"idle (last seen {d.get('last_seen', '')})"})
            return {"ready": self.ready, "baseline": len(self.baseline), "dhcp": self.dhcp_status,
                    "dhcp_events": self.dhcp_events,
                    "active": sum(d["active"] for d in devs), "devices": devs,
                    "alerts": list(self.alerts[:20])}


if __name__ == "__main__":
    import sys
    if "--dhcp" in sys.argv:                      # test: print every DHCP join packet heard (Ctrl+C to stop)
        sock = open_dhcp_socket()
        print("Listening for DHCP join broadcasts on UDP 67 ... connect a device to the Wi-Fi now")
        while True:
            try:
                pkt, src = sock.recvfrom(2048)
            except socket.timeout:
                continue
            info = parse_dhcp(pkt)
            if info:
                print(time.strftime("%H:%M:%S"), info, "maker:", _maker(info["mac"]), flush=True)
    print("Sweeping", [str(n) for n in _subnets()], "...")
    sweep(); time.sleep(3)
    for mac, d in scan().items():
        print(f"{d['ip']:16s} {mac}  {d['state']:10s} {d['maker']}")
