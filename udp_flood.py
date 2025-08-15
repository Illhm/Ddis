#!/usr/bin/env python3
"""
HTTP keep-alive load tester (1 koneksi per thread, banyak request berurutan)
- Paralel via beberapa thread
- Tiap thread mempertahankan 1 koneksi (keep-alive) dan loop kirim GET
- Rate per-thread (PER_THREAD_RPS) agar tidak jadi flooder
- ALLOWLIST untuk IP publik (gunakan hanya pada host yang kamu kuasai/berizin)

Butuh: pip install requests
"""

import requests, threading, time, socket, ipaddress, sys
from urllib.parse import urlparse

# ===== Konfigurasi =====
TARGET_URL       = "http://139.99.61.184/~bansosrz7/"  # ganti ke URL situsmu
THREADS          = 400000          # banyaknya koneksi paralel (1 koneksi = 1 thread)
PER_THREAD_RPS   = 5000          # request per detik per thread (total RPS = THREADS * PER_THREAD_RPS)
DURATION_SEC     = 1000         # durasi uji
TIMEOUT_S        = 10         # timeout per request

# ALLOWLIST untuk target publik (berdasar IP hasil DNS)
ALLOWLIST        = {"139.99.61.184"}

# ===== State & metriks =====
stop_evt   = threading.Event()
ok_count   = [0] * THREADS
err_count  = [0] * THREADS
bytes_recv = [0] * THREADS
sec_lats   = []               # latensi-ms untuk window 1 detik (digunakan reporter)
_hist_bins = [10,20,50,100,200,500,1000,2000,5000,10000, 10**9]  # ms
_hist_cnts = [0]*len(_hist_bins)
locks      = [threading.Lock() for _ in range(THREADS)]
g_lock     = threading.Lock()  # untuk sec_lats & histogram

HEADERS = {
    "User-Agent": "py-keepalive-loadtester/1.0",
    "Accept": "*/*",
    "Connection": "keep-alive",   # penting: minta koneksi dipertahankan
}

def _p_from_list(v, p):
    if not v: return None
    v = sorted(v)
    k = max(0, min(len(v)-1, int(round((p/100)*(len(v)-1)))))
    return v[k]

def _hist_add(ms):
    for i, b in enumerate(_hist_bins):
        if ms <= b:
            _hist_cnts[i] += 1
            break

def _p_from_hist(p):
    total = sum(_hist_cnts)
    if total == 0: return None
    target = p/100.0 * total
    acc = 0
    for i, c in enumerate(_hist_cnts):
        acc += c
        if acc >= target:
            return _hist_bins[i]
    return _hist_bins[-1]

def _resolve_target_ip(url: str) -> str:
    host = urlparse(url).hostname
    if not host:
        print("[STOP] URL tidak valid."); sys.exit(1)
    try:
        return socket.gethostbyname(host)
    except Exception as e:
        print(f"[STOP] Gagal resolve host {host}: {e}"); sys.exit(1)

def _ensure_allowed(url: str):
    ip = _resolve_target_ip(url)
    ipobj = ipaddress.ip_address(ip)
    is_public = not (ipobj.is_private or ipobj.is_loopback or ipobj.is_link_local)
    if is_public and ip not in ALLOWLIST:
        print(f"[STOP] Target {ip} adalah IP publik dan tidak ada di ALLOWLIST.")
        sys.exit(1)

def worker(idx: int, end_ts: float):
    # 1 session per thread -> 1 koneksi persist (pool size=1)
    sess = requests.Session()
    sess.headers.update(HEADERS)
    # Pasang adapter dengan pool_maxsize=1 agar thread ini pakai satu koneksi saja
    from requests.adapters import HTTPAdapter
    adapter = HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=0, pool_block=True)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)

    interval = 0.2 / max(1, PER_THREAD_RPS)
    next_ts = time.time()
    while not stop_evt.is_set() and time.time() < end_ts:
        now = time.time()
        if now < next_ts:
            time.sleep(min(0.001, next_ts - now))
            continue
        t0 = time.perf_counter()
        try:
            r = sess.get(TARGET_URL, timeout=TIMEOUT_S, allow_redirects=False)
            body = r.content  # konsumsi respons agar koneksi bisa dipakai ulang
            dt_ms = (time.perf_counter() - t0) * 1000.0
            with locks[idx]:
                if 200 <= r.status_code < 400:
                    ok_count[idx] += 1
                else:
                    err_count[idx] += 1
                bytes_recv[idx] += len(body)
            with g_lock:
                sec_lats.append(dt_ms); _hist_add(dt_ms)
        except Exception:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            with locks[idx]:
                err_count[idx] += 1
            with g_lock:
                sec_lats.append(dt_ms); _hist_add(dt_ms)
        finally:
            next_ts += interval

    sess.close()

def reporter(end_ts: float):
    last = time.perf_counter()
    prev_bytes = 0
    while not stop_evt.is_set():
        now = time.perf_counter()
        if now - last >= 1.0:
            last = now
            total_ok  = sum(ok_count)
            total_err = sum(err_count)
            total_b   = sum(bytes_recv)
            inst_b    = total_b - prev_bytes
            prev_bytes = total_b
            with g_lock:
                p50 = _p_from_list(sec_lats, 50)
                p95 = _p_from_list(sec_lats, 95)
                sec_lats.clear()
            mbps = (inst_b * 8) / 1e6
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            p50s = f"{p50:.0f}ms" if p50 is not None else "-"
            p95s = f"{p95:.0f}ms" if p95 is not None else "-"
            print(f"{ts} | OK={total_ok} ERR={total_err} | IN≈{mbps:7.2f} Mbps | p50={p50s} p95={p95s} | total={total_b/1e6:,.2f} MB")
        if time.time() >= end_ts:
            break
        time.sleep(0.05)

def main():
    print(f"Target : {TARGET_URL}")
    print(f"Threads: {THREADS} | per-thread RPS: {PER_THREAD_RPS} | Duration: {DURATION_SEC}s | Timeout: {TIMEOUT_S}s")
    _ensure_allowed(TARGET_URL)

    end_ts = time.time() + DURATION_SEC
    rep = threading.Thread(target=reporter, args=(end_ts,), daemon=True)
    rep.start()

    threads = []
    for i in range(THREADS):
        t = threading.Thread(target=worker, args=(i, end_ts), daemon=True)
        t.start()
        threads.append(t)

    try:
        while time.time() < end_ts:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan oleh user.")
    finally:
        stop_evt.set()
        for t in threads: t.join(timeout=1.0)

    total_ok  = sum(ok_count)
    total_err = sum(err_count)
    total_b   = sum(bytes_recv)
    p50_all   = _p_from_hist(50) or 0
    p95_all   = _p_from_hist(95) or 0
    print(f"\nSelesai. OK={total_ok} ERR={total_err} | Total={total_b/1e6:.2f} MB | p50≈{p50_all:.0f}ms p95≈{p95_all:.0f}ms")

if __name__ == "__main__":
    main()
