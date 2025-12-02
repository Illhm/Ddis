# HTTP Slowloris Check

Script Python untuk menguji perilaku server web terhadap serangan "slow headers" (gaya Slowloris) dengan cara yang aman dan terkontrol.

## ⚠️ PERINGATAN PENTING

**Script ini hanya untuk tujuan educational dan testing pada infrastruktur milik sendiri atau dengan izin eksplisit dari pemilik server.**

Penggunaan script ini tanpa izin pada sistem yang bukan milik Anda adalah **ILEGAL** dan dapat melanggar:
- Computer Fraud and Abuse Act (CFAA) di Amerika Serikat
- Computer Misuse Act di Inggris
- Undang-Undang ITE di Indonesia
- Hukum serupa di negara lain

## Apa itu Slowloris?

Slowloris adalah jenis serangan Denial of Service (DoS) yang bekerja dengan:
1. Membuka banyak koneksi HTTP ke server target
2. Mengirim header HTTP secara perlahan dan tidak lengkap
3. Menjaga koneksi tetap terbuka selama mungkin
4. Menghabiskan resource server (connection pool)

Script ini **BUKAN** untuk melakukan serangan, tetapi untuk **menguji apakah server Anda rentan** terhadap serangan semacam ini.

## Fitur

- ✅ Testing aman dengan jumlah koneksi terbatas
- ✅ Allowlist IP untuk mencegah penyalahgunaan
- ✅ Support HTTP dan HTTPS
- ✅ Logging terstruktur dengan level yang jelas
- ✅ Hasil testing yang mudah dibaca
- ✅ Tidak memerlukan dependencies eksternal (stdlib only)

## Instalasi

Tidak ada dependencies eksternal yang diperlukan. Script ini hanya menggunakan Python standard library.

```bash
# Clone repository
git clone https://github.com/Illhm/Ddis.git
cd Ddis

# Pastikan Python 3.6+ terinstall
python3 --version
```

## Konfigurasi

Edit file `http_slowloris_check.py` dan sesuaikan konfigurasi:

```python
# Target yang akan ditest (WAJIB ada di ALLOWLIST)
TARGET = "http://139.99.61.184"

# Path yang akan direquest
PATH = "/"

# Port yang akan ditest
PORTS = [80, 443]

# Jumlah koneksi per port (gunakan nilai kecil untuk testing aman)
CONNS_PER_PORT = 5

# Durasi testing dalam detik
DURATION_SEC = 30

# Interval pengiriman header dummy
INTERVAL_SEC = 5

# ALLOWLIST - WAJIB diisi dengan IP yang Anda miliki/izinkan
ALLOWLIST = {
    "139.99.61.184",  # Ganti dengan IP server Anda
}
```

## Penggunaan

```bash
# Jalankan script
python3 http_slowloris_check.py
```

Output akan menampilkan:
- Status koneksi untuk setiap port
- Berapa lama koneksi bertahan
- Interpretasi hasil (apakah server rentan atau sudah terlindungi)

### Contoh Output

```
2025-12-02 10:00:00 - INFO - ============================================================
2025-12-02 10:00:00 - INFO - HTTP Slowloris Check - Server Behavior Testing Tool
2025-12-02 10:00:00 - INFO - ============================================================
2025-12-02 10:00:00 - INFO - Target: 139.99.61.184 (139.99.61.184) | path=/
2025-12-02 10:00:00 - INFO - Durasi: 30s | interval header: 5s | conns/port: 5
2025-12-02 10:00:00 - INFO - Total koneksi: 10

[PORT 80] connections: 5
  - kept open >= 30s : 0
  - closed early     : 5 (median close at ~10.2s)
  * Interpretasi: server menutup koneksi cepat (mitigasi header timeout tampak aktif).
```

## Interpretasi Hasil

### Server Rentan
Jika banyak koneksi bertahan hingga durasi penuh (30 detik atau lebih):
- Server **mungkin rentan** terhadap serangan Slowloris
- Pertimbangkan untuk mengkonfigurasi timeout yang lebih ketat
- Implementasi rate limiting per IP

### Server Terlindungi
Jika koneksi ditutup lebih awal (< 10 detik):
- Server **sudah memiliki mitigasi** yang baik
- Timeout header sudah dikonfigurasi dengan benar
- Kemungkinan ada rate limiting atau firewall yang aktif

## Mitigasi Slowloris untuk Server Anda

Jika testing menunjukkan server Anda rentan, pertimbangkan:

### Nginx
```nginx
# Timeout untuk membaca header client
client_header_timeout 10s;

# Timeout untuk membaca body client
client_body_timeout 10s;

# Limit koneksi per IP
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn addr 10;
```

### Apache
```apache
# Timeout untuk request
Timeout 10

# Request read timeout
RequestReadTimeout header=10-20,MinRate=500 body=20,MinRate=500

# Limit koneksi dengan mod_reqtimeout dan mod_qos
```

### HAProxy
```
timeout client 10s
timeout http-request 10s
```

## Struktur Kode

```
.
├── http_slowloris_check.py    # Script utama
├── README.md                   # Dokumentasi ini
├── requirements.txt            # Dependencies (kosong, stdlib only)
├── .gitignore                  # Git ignore file
└── .github/
    └── workflows/
        └── http-slowloris-check.yml  # GitHub Actions workflow
```

## GitHub Actions

Repository ini menggunakan GitHub Actions untuk automated testing. Workflow dikonfigurasi untuk:
- Hanya berjalan pada manual dispatch (tidak otomatis pada push)
- Testing pada Python 3.x
- Validasi syntax dan struktur kode

## Kontribusi

Kontribusi sangat diterima! Silakan:
1. Fork repository ini
2. Buat branch untuk fitur/perbaikan Anda
3. Commit perubahan Anda
4. Push ke branch Anda
5. Buat Pull Request

## Lisensi

Script ini disediakan "as is" untuk tujuan educational. Penggunaan untuk tujuan ilegal adalah tanggung jawab pengguna.

## Disclaimer

Penulis tidak bertanggung jawab atas penyalahgunaan script ini. Script ini dibuat untuk:
- Testing keamanan server milik sendiri
- Pembelajaran tentang serangan DoS dan mitigasinya
- Validasi konfigurasi server web

**Gunakan dengan bijak dan bertanggung jawab!**

## Referensi

- [Slowloris Attack - OWASP](https://owasp.org/www-community/attacks/Slowloris)
- [HTTP Slow Attacks - Cloudflare](https://www.cloudflare.com/learning/ddos/ddos-attack-tools/slowloris/)
- [Mitigating Slowloris - Nginx](https://www.nginx.com/blog/mitigating-ddos-attacks-with-nginx-and-nginx-plus/)

## Kontak

Untuk pertanyaan atau laporan bug, silakan buat issue di repository ini.

---

**Remember: With great power comes great responsibility. Use this tool ethically!**
