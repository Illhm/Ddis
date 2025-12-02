# Slowloris Checker v2.0

**Professional HTTP Slowloris Vulnerability Scanner**

[![CI/CD](https://github.com/Illhm/Ddis/actions/workflows/test.yml/badge.svg)](https://github.com/Illhm/Ddis/actions/workflows/test.yml)
[![Security Scan](https://github.com/Illhm/Ddis/actions/workflows/security-scan.yml/badge.svg)](https://github.com/Illhm/Ddis/actions/workflows/security-scan.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

`slowloris-checker` adalah tool security testing yang dirancang untuk menguji kerentanan server web terhadap serangan **Slowloris** dengan cara yang aman, terkontrol, dan profesional. Tool ini dikembangkan dari script sederhana menjadi solusi enterprise-grade dengan fitur lengkap.

## ⚠️ PERINGATAN PENTING

**Tool ini hanya untuk tujuan educational dan testing pada infrastruktur milik sendiri atau dengan izin eksplisit dari pemilik server.**

Penggunaan tool ini tanpa izin pada sistem yang bukan milik Anda adalah **ILEGAL** dan dapat melanggar hukum di berbagai negara. Gunakan dengan bijak dan bertanggung jawab!

## Fitur Utama

- **CLI Interface Profesional**: Interface command-line yang powerful dan mudah digunakan.
- **Async/Await Architecture**: Performa tinggi dengan `asyncio` untuk scanning yang cepat.
- **Multiple Output Formats**: Hasil dalam format `console`, `json`, `csv`, dan `html`.
- **Scoring System**: Skor 0-100 untuk mengukur tingkat proteksi server.
- **HTML Reports**: Laporan HTML yang indah dan mudah dibaca.
- **CI/CD Integration**: Mode CI/CD dengan exit codes untuk automation.
- **Configuration Files**: Dukungan file konfigurasi YAML/JSON untuk batch testing.
- **Plugin System**: Extensible dengan plugin untuk notifikasi, custom analysis, dll.
- **Docker Support**: Siap digunakan dengan Docker dan Docker Compose.
- **Zero Dependencies**: Tidak memerlukan dependencies eksternal untuk core functionality.

## Instalasi

### Menggunakan `pip`

```bash
# Install dari PyPI (coming soon)
pip install slowloris-checker

# Install dari source
git clone https://github.com/Illhm/Ddis.git
cd Ddis
pip install -e .
```

### Menggunakan Docker

```bash
# Build Docker image
docker build -t slowloris-checker .

# Run via Docker
docker run --rm slowloris-checker http://example.com

# Run via Docker Compose
docker-compose up
```

## Penggunaan

### Basic Usage

```bash
# Scan target dengan konfigurasi default
slowloris-checker http://example.com
```

### Advanced Usage

```bash
# Scan dengan custom options
slowloris-checker http://example.com \
  --ports 80,443,8080 \
  --connections 10 \
  --duration 60 \
  --interval 5 \
  --timeout 10 \
  --output json \
  --file results.json \
  --report report.html \
  --verbose
```

### CI/CD Mode

```bash
# Fail jika score di bawah 80
slowloris-checker http://staging.example.com \
  --ci \
  --fail-threshold 80
```

### CLI Options

```
usage: slowloris-checker [-h] [-v] [-p PORTS] [-c N] [--path PATH] [-d SEC]
                         [-i SEC] [-t SEC] [-o {console,json,csv}] [-f FILE]
                         [--report FILE] [--verbose] [--debug] [--quiet]
                         [--allowlist IP] [--no-allowlist-check] [--ci]
                         [--fail-threshold SCORE]
                         [target]

Professional HTTP Slowloris Vulnerability Scanner

positional arguments:
  target                Target URL (e.g., http://example.com)

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit

target options:
  -p PORTS, --ports PORTS
                        Comma-separated list of ports to scan (default: 80,443)
  -c N, --connections N
                        Number of connections per port (default: 5, max: 50)
  --path PATH           HTTP path to request (default: /)

timing options:
  -d SEC, --duration SEC
                        Test duration in seconds (default: 30, max: 300)
  -i SEC, --interval SEC
                        Interval between headers in seconds (default: 5)
  -t SEC, --timeout SEC
                        Connection timeout in seconds (default: 10)

output options:
  -o {console,json,csv}, --output {console,json,csv}
                        Output format (default: console)
  -f FILE, --file FILE  Output file (default: stdout)
  --report FILE         Generate HTML report

logging options:
  --verbose             Verbose output
  --debug               Debug output
  --quiet               Quiet mode (errors only)

... (and more)
```

## Contoh Output

### Console Output

```
======================================================================
SCAN RESULTS
======================================================================
Target:    http://example.com
IP:        93.184.216.34
Scan ID:   scan_123456789abc
Duration:  31.2s
======================================================================

OVERALL ASSESSMENT
----------------------------------------------------------------------
Score:  45.0/100
Status: ✗ VULNERABLE

⚠️  Vulnerable ports: 443
✓  Protected ports:  80

PORT ANALYSIS
----------------------------------------------------------------------

Port 80:
  Status:      ✓✓ EXCELLENT
  Score:       95.0/100
  Connections: 5 total, 5 successful, 0 failed
  Kept open:   0 (0.0%)
  Duration:    median=8.5s, mean=8.6s

Port 443:
  Status:      ✗ VULNERABLE
  Score:       -5.0/100
  Connections: 5 total, 5 successful, 0 failed
  Kept open:   5 (100.0%)
  Duration:    median=30.1s, mean=30.1s

RECOMMENDATIONS
----------------------------------------------------------------------
⚠️  Your server needs better protection against Slowloris attacks.

Specific actions:
  1. Port 443: Configure shorter header timeout (current median: 30.1s)

General recommendations:
  • Configure client_header_timeout (Nginx) or RequestReadTimeout (Apache)
  • Implement rate limiting per IP address
  • Consider using a WAF (Web Application Firewall)

======================================================================
Scan completed successfully
======================================================================
```

### HTML Report

Laporan HTML yang interaktif dan mudah dibaca akan digenerate jika menggunakan `--report report.html`.

## Arsitektur

Tool ini dibangun dengan arsitektur modular:

- **CLI Interface**: `argparse` untuk parsing arguments.
- **Configuration Manager**: Load config dari CLI, file, dan environment variables.
- **Core Engine**: `asyncio` untuk scanning, `dataclasses` untuk models.
- **Output Handlers**: Console, JSON, CSV, HTML.
- **Plugin System**: Extensible untuk notifikasi, dll.

## Struktur Project

```
slowloris-checker/
├── slowloris_checker/     # Source code
│   ├── core/              # Core logic (scanner, models)
│   ├── output/            # Output handlers
│   ├── plugins/           # Plugin system
│   ├── utils/             # Utility functions
│   ├── cli.py             # CLI interface
│   └── __main__.py        # Entry point
├── tests/                 # Unit & integration tests
├── docs/                  # Documentation
├── examples/              # Example configs
├── .github/               # GitHub Actions workflows
├── setup.py               # Installation script
├── Dockerfile             # Docker image
└── README.md              # This file
```

## Mitigasi Slowloris

Jika server Anda rentan, pertimbangkan:

### Nginx
```nginx
# Timeout untuk header client
client_header_timeout 10s;

# Limit koneksi per IP
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn addr 10;
```

### Apache
```apache
# Timeout
Timeout 10
RequestReadTimeout header=10-20,MinRate=500

# Load mod_reqtimeout dan mod_qos
LoadModule reqtimeout_module modules/mod_reqtimeout.so
```

## Kontribusi

Kontribusi sangat diterima! Silakan fork repository ini, buat branch, dan buat Pull Request.

## Lisensi

MIT License
