"""Safe, local-only attack simulator for the KAVACH demo video. Touches ONLY this device (127.0.0.1 or the given
target on your own network). Run it in a second terminal while the dashboard's Network tab is open.

  python simulate_attack.py scan               # probe 40 ports on this device  -> PORT_SCAN alert
  python simulate_attack.py exfil              # 300 MB burst through a local socket -> TRAFFIC_SPIKE alert
  python simulate_attack.py backdoor           # open a listener on port 4444  -> NEW_LISTENER alert
  python simulate_attack.py scan --target 192.168.1.50   # scan your own Pi from your laptop (same Wi-Fi)
"""
import argparse, socket, threading, time


def scan(target, ports=range(8000, 8040), rounds=3):
    for _ in range(rounds):
        for p in ports:
            s = socket.socket(); s.settimeout(0.2)
            try:
                s.connect_ex((target, p))
            finally:
                s.close()
        time.sleep(0.5)
    print(f"probed {len(list(ports))} ports on {target} x{rounds}")


def exfil(mb=300):
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0)); srv.listen(1); port = srv.getsockname()[1]

    def sink():
        c, _ = srv.accept()
        while c.recv(1 << 20):
            pass
    threading.Thread(target=sink, daemon=True).start()
    cli = socket.create_connection(("127.0.0.1", port))
    chunk = b"x" * (1 << 20)
    t = time.time()
    for _ in range(mb):
        cli.sendall(chunk)
        time.sleep(0.01)
    cli.close()
    print(f"sent {mb} MB in {time.time() - t:.1f} s")


def backdoor(seconds=60, port=4444):
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port)); srv.listen(1)
    print(f"listening on port {port} for {seconds} s (simulated backdoor)")
    time.sleep(seconds)
    srv.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["scan", "exfil", "backdoor"])
    ap.add_argument("--target", default="127.0.0.1")
    a = ap.parse_args()
    {"scan": lambda: scan(a.target), "exfil": exfil, "backdoor": backdoor}[a.mode]()
