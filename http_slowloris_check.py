#!/usr/bin/env python3
"""
http_slowloris_check.py
Cek ringan perilaku server terhadap "slow headers" (gaya Slowloris)
- Koneksi sangat sedikit & berdurasi pendek (aman)
- Tanpa membanjiri server; hanya observasi timeout/penutupan koneksi
- Gunakan hanya untuk host milikmu/berizin (ALLOWLIST diterapkan)

PERINGATAN: Script ini hanya untuk testing server milik sendiri atau dengan izin eksplisit.
Penggunaan tanpa izin adalah ilegal dan tidak etis.

Stdlib only: socket, ssl, time, threading, logging
"""

import socket
import ssl
import time
import threading
import random
import sys
import ipaddress
import logging
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ========= KONFIGURASI =========
TARGET = "http://139.99.61.184"  # bisa http://IP atau http(s)://domain
PATH = "/"  # path yang diminta di baris pertama
PORTS = [80, 443]  # port yang dicek
CONNS_PER_PORT = 5  # koneksi paralel per port (nilai kecil untuk testing aman)
DURATION_SEC = 30  # durasi observasi maksimal (dikurangi dari 300 ke 30 detik)
INTERVAL_SEC = 5  # jeda antar header "dummy" (dikurangi dari 50 ke 5 detik)
CONNECT_TIMEOUT = 10  # detik (diperbaiki dari 1000000)
SOCKET_TIMEOUT = 10  # detik (read/send timeout)

# ALLOWLIST IP publik - WAJIB diisi dengan IP yang Anda miliki/izinkan
ALLOWLIST = {
    "139.99.61.184",
}

# ========= UTIL =========
def is_ip(host: str) -> bool:
    """Check if host is a valid IP address"""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def resolve_host(host: str) -> str:
    """Resolve hostname to IP address"""
    if is_ip(host):
        return host
    try:
        return socket.gethostbyname(host)
    except socket.gaierror as e:
        logger.error(f"Failed to resolve host {host}: {e}")
        sys.exit(1)


def ensure_allowed(host: str):
    """Ensure target is in allowlist or is private IP"""
    ip = resolve_host(host)
    try:
        ipobj = ipaddress.ip_address(ip)
    except ValueError as e:
        logger.error(f"Invalid IP address {ip}: {e}")
        sys.exit(1)
    
    is_public = not (ipobj.is_private or ipobj.is_loopback or ipobj.is_link_local)
    
    if is_public and ip not in ALLOWLIST:
        logger.error(f"Target {ip} adalah IP publik dan tidak ada di ALLOWLIST.")
        logger.error("Untuk keamanan, hanya IP dalam ALLOWLIST yang dapat ditest.")
        sys.exit(1)
    
    if is_public:
        logger.warning(f"Testing public IP {ip} - pastikan Anda memiliki izin!")


# ========= CORE =========
class ConnResult:
    """Store connection result data"""
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
    """Create socket connection with timeout"""
    try:
        s = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
        s.settimeout(SOCKET_TIMEOUT)
        return s
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        logger.debug(f"Failed to connect to {host}:{port} - {e}")
        raise


def wrap_tls_if_needed(sock, host: str, port: int, scheme: str):
    """Wrap socket with TLS if needed"""
    if scheme == "https" or port == 443:
        ctx = ssl.create_default_context()
        # Non-verifying: kita hanya observasi perilaku, bukan validasi cert
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        server_hostname = host if not is_ip(host) else None
        try:
            sock = ctx.wrap_socket(sock, server_hostname=server_hostname)
        except ssl.SSLError as e:
            logger.debug(f"SSL handshake failed: {e}")
            raise
    return sock


def send_slow_headers(host_header: str, sock, res: ConnResult, end_ts: float):
    """Send slow headers to test server behavior"""
    # Baris awal + header wajib, TANPA CRLF ganda di akhir
    first = (
        f"GET {PATH} HTTP/1.1\r\n"
        f"Host: {host_header}\r\n"
        f"User-Agent: slowloris-check/1.0\r\n"
    ).encode("ascii", "ignore")

    try:
        sock.sendall(first)
        res.sent_lines += 3
    except Exception as e:
        res.error = f"send first: {e}"
        return

    # Kirim header dummy kecil tiap INTERVAL_SEC
    while time.time() < end_ts:
        line = f"X-Dummy-{random.randint(1000,9999)}: {random.randint(0,999999)}\r\n".encode(
            "ascii", "ignore"
        )
        try:
            sock.sendall(line)
            res.sent_lines += 1
            # Coba baca non-blocking sedikit untuk mendeteksi pemutusan sisi server
            try:
                sock.settimeout(0.001)
                data = sock.recv(1)
                if data:
                    # Kalau server tiba-tiba kirim respons, berarti ia menutup/merespons
                    logger.debug("Server sent response early")
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
    """Worker thread for testing connection"""
    res = ConnResult(port)
    result_list.append(res)
    s = None  # Initialize socket variable
    
    try:
        s = make_socket(host, port)
        s = wrap_tls_if_needed(s, host, port, scheme)
        send_slow_headers(host, s, res, end_ts)
    except Exception as e:
        res.error = f"connect/error: {e}"
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass
        if not res.closed_at:
            # kalau masih terbuka sampai selesai durasi
            res.closed_at = time.time()


def summarize(results: list, port: int):
    """Summarize results for a specific port"""
    port_results = [r for r in results if r.port == port]
    kept = [r for r in port_results if r.error is None and r.duration >= DURATION_SEC - 0.5]
    early = [r for r in port_results if r.error or r.duration < DURATION_SEC - 0.5]
    
    logger.info(f"\n[PORT {port}] connections: {len(port_results)}")
    logger.info(f"  - kept open >= {DURATION_SEC}s : {len(kept)}")
    
    if early:
        durations = sorted(r.duration for r in early)
        med = durations[len(durations) // 2]
        logger.info(f"  - closed early                : {len(early)} (median close at ~{med:.1f}s)")
    
    # Catatan interpretasi
    if kept:
        logger.info("  * Interpretasi: server menoleransi header lambat cukup lama.")
        logger.info("    Periksa/ketatkan: client_header_timeout / read_header_timeout, rate/conn limit per IP.")
    else:
        logger.info("  * Interpretasi: server menutup koneksi cepat (mitigasi header timeout tampak aktif).")


def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("HTTP Slowloris Check - Server Behavior Testing Tool")
    logger.info("=" * 60)
    logger.info("PERINGATAN: Gunakan hanya pada server milik sendiri atau dengan izin eksplisit!")
    logger.info("")
    
    u = urlparse(TARGET)
    scheme = u.scheme or "http"
    host = u.hostname or u.path  # simple parse untuk 'http://ip'
    
    if not host:
        logger.error("TARGET tidak valid.")
        sys.exit(1)

    ensure_allowed(host)
    ip = resolve_host(host)
    
    logger.info(f"Target: {host} ({ip}) | path={PATH}")
    logger.info(f"Durasi: {DURATION_SEC}s | interval header: {INTERVAL_SEC}s | conns/port: {CONNS_PER_PORT}")
    logger.info(f"Total koneksi: {CONNS_PER_PORT * len(PORTS)}")
    logger.info("")

    end_ts = time.time() + DURATION_SEC
    results = []
    threads = []

    logger.info("Memulai testing...")
    for port in PORTS:
        for i in range(CONNS_PER_PORT):
            t = threading.Thread(
                target=worker,
                args=(host, port, scheme, results, end_ts),
                daemon=True,
                name=f"Worker-{port}-{i}"
            )
            t.start()
            threads.append(t)
            # Small delay to avoid overwhelming the system
            time.sleep(0.01)

    try:
        while time.time() < end_ts:
            active = sum(1 for t in threads if t.is_alive())
            logger.debug(f"Active threads: {active}/{len(threads)}")
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n[INFO] Dihentikan oleh user.")

    # join sebentar
    logger.info("Menunggu threads selesai...")
    for t in threads:
        t.join(timeout=2.0)

    # Ringkasan per port
    logger.info("\n" + "=" * 60)
    logger.info("HASIL TESTING")
    logger.info("=" * 60)
    for p in PORTS:
        summarize(results, p)

    # Detail ringan
    logger.info("\nDetail koneksi:")
    for r in results:
        status = (
            "kept_to_end"
            if (r.error is None and r.duration >= DURATION_SEC - 0.5)
            else (r.error or "closed")
        )
        logger.info(
            f"  - port {r.port}: duration={r.duration:.1f}s, sent_lines={r.sent_lines}, status={status}"
        )
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing selesai!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
