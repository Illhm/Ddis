# Design: Professional HTTP Slowloris Checker

## Visi

Mengembangkan tool dari script sederhana menjadi **enterprise-grade security testing tool** dengan fitur:
- CLI interface yang powerful
- Multiple output formats (JSON, CSV, HTML report)
- Async/await untuk performance
- Plugin system untuk extensibility
- Comprehensive logging dan monitoring
- CI/CD integration ready

## Arsitektur Baru

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface                          │
│  (argparse, rich for beautiful output)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                  Configuration Manager                      │
│  - Load from file (YAML/JSON)                               │
│  - Environment variables                                    │
│  - Command line overrides                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                    Core Engine                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Scanner    │  │   Analyzer   │  │   Reporter   │     │
│  │   Module     │  │   Module     │  │   Module     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                  Output Handlers                            │
│  - Console (pretty tables, colors)                          │
│  - JSON (for automation)                                    │
│  - CSV (for spreadsheets)                                   │
│  - HTML (beautiful reports)                                 │
│  - Webhook (Slack, Discord, etc)                            │
└─────────────────────────────────────────────────────────────┘
```

## Fitur Professional

### 1. CLI Interface
```bash
# Basic usage
slowloris-check http://example.com

# Advanced usage
slowloris-check http://example.com \
  --ports 80,443,8080 \
  --connections 10 \
  --duration 60 \
  --interval 5 \
  --timeout 10 \
  --output json \
  --report report.html \
  --verbose

# Config file
slowloris-check --config config.yaml

# Multiple targets
slowloris-check --targets targets.txt

# CI/CD mode
slowloris-check http://example.com --ci --threshold 80
```

### 2. Configuration File Support
```yaml
# config.yaml
targets:
  - url: http://example.com
    ports: [80, 443]
    connections: 5
  - url: http://another.com
    ports: [8080]
    connections: 3

global:
  duration: 30
  interval: 5
  timeout: 10
  
output:
  format: json
  file: results.json
  console: true
  
reporting:
  html: true
  html_file: report.html
  
notifications:
  slack:
    enabled: true
    webhook: https://hooks.slack.com/...
```

### 3. Async/Await Architecture
```python
# Gunakan asyncio untuk performance
async def scan_target(target):
    tasks = []
    for port in target.ports:
        for i in range(target.connections):
            task = asyncio.create_task(
                worker_async(target, port)
            )
            tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### 4. Multiple Output Formats

#### JSON Output
```json
{
  "scan_id": "scan_20251202_123456",
  "timestamp": "2025-12-02T12:34:56Z",
  "target": {
    "url": "http://example.com",
    "ip": "93.184.216.34"
  },
  "results": {
    "80": {
      "total_connections": 5,
      "kept_open": 0,
      "closed_early": 5,
      "median_duration": 8.5,
      "status": "protected",
      "score": 95
    },
    "443": {
      "total_connections": 5,
      "kept_open": 2,
      "closed_early": 3,
      "median_duration": 25.3,
      "status": "vulnerable",
      "score": 40
    }
  },
  "overall": {
    "status": "vulnerable",
    "score": 67.5,
    "recommendation": "Configure timeout on port 443"
  }
}
```

#### HTML Report
```html
<!DOCTYPE html>
<html>
<head>
    <title>Slowloris Check Report</title>
    <style>/* Beautiful CSS */</style>
</head>
<body>
    <h1>Security Assessment Report</h1>
    <div class="summary">
        <h2>Executive Summary</h2>
        <p>Target: example.com (93.184.216.34)</p>
        <p>Overall Score: 67.5/100</p>
        <p>Status: <span class="vulnerable">VULNERABLE</span></p>
    </div>
    
    <div class="details">
        <h2>Port Analysis</h2>
        <table>
            <tr>
                <th>Port</th>
                <th>Status</th>
                <th>Score</th>
                <th>Details</th>
            </tr>
            <tr>
                <td>80</td>
                <td class="protected">Protected</td>
                <td>95</td>
                <td>All connections closed within 10s</td>
            </tr>
            <tr>
                <td>443</td>
                <td class="vulnerable">Vulnerable</td>
                <td>40</td>
                <td>2/5 connections stayed open > 30s</td>
            </tr>
        </table>
    </div>
    
    <div class="recommendations">
        <h2>Recommendations</h2>
        <ul>
            <li>Configure client_header_timeout on port 443</li>
            <li>Implement rate limiting per IP</li>
            <li>Consider using a WAF</li>
        </ul>
    </div>
</body>
</html>
```

### 5. Scoring System
```python
def calculate_score(results):
    """
    Score 0-100:
    - 90-100: Excellent protection
    - 70-89:  Good protection
    - 50-69:  Moderate protection
    - 30-49:  Weak protection
    - 0-29:   Vulnerable
    """
    kept_open = len([r for r in results if r.duration >= threshold])
    total = len(results)
    
    protection_rate = (total - kept_open) / total * 100
    
    # Adjust based on median close time
    median_time = calculate_median_close_time(results)
    if median_time < 10:
        bonus = 10
    elif median_time < 20:
        bonus = 5
    else:
        bonus = 0
    
    score = min(100, protection_rate + bonus)
    return score
```

### 6. Plugin System
```python
# plugins/slack_notifier.py
class SlackNotifier(Plugin):
    def on_scan_complete(self, results):
        message = self.format_message(results)
        self.send_to_slack(message)

# plugins/custom_analyzer.py
class CustomAnalyzer(Plugin):
    def analyze(self, results):
        # Custom analysis logic
        return custom_insights
```

### 7. CI/CD Integration
```bash
# Exit code based on threshold
slowloris-check http://staging.example.com \
  --ci \
  --threshold 80 \
  --fail-on-vulnerable

# Exit 0 if score >= 80
# Exit 1 if score < 80
```

### 8. Monitoring & Metrics
```python
# Prometheus metrics
slowloris_scan_duration_seconds
slowloris_connections_total
slowloris_connections_kept_open
slowloris_target_score

# Logging
2025-12-02 12:34:56 INFO  Starting scan for example.com
2025-12-02 12:34:57 DEBUG Connected to 93.184.216.34:80
2025-12-02 12:35:27 INFO  Scan completed in 31.2s
2025-12-02 12:35:27 WARN  Port 443 is vulnerable (score: 40)
```

## Struktur Project

```
slowloris-checker/
├── slowloris_checker/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── cli.py               # CLI interface
│   ├── config.py            # Configuration management
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scanner.py       # Core scanning logic
│   │   ├── analyzer.py      # Result analysis
│   │   ├── reporter.py      # Report generation
│   │   └── models.py        # Data models
│   ├── output/
│   │   ├── __init__.py
│   │   ├── console.py       # Console output
│   │   ├── json_output.py   # JSON output
│   │   ├── csv_output.py    # CSV output
│   │   └── html_output.py   # HTML report
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py          # Plugin base class
│   │   └── slack.py         # Slack integration
│   └── utils/
│       ├── __init__.py
│       ├── network.py       # Network utilities
│       └── validation.py    # Input validation
├── tests/
│   ├── __init__.py
│   ├── test_scanner.py
│   ├── test_analyzer.py
│   └── test_output.py
├── docs/
│   ├── README.md
│   ├── USAGE.md
│   ├── API.md
│   └── PLUGINS.md
├── examples/
│   ├── config.yaml
│   ├── targets.txt
│   └── custom_plugin.py
├── .github/
│   └── workflows/
│       ├── test.yml
│       ├── release.yml
│       └── security-scan.yml
├── setup.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
```

## Dependencies

### Core
```
# requirements.txt
aiohttp>=3.9.0        # Async HTTP
pydantic>=2.0.0       # Data validation
pyyaml>=6.0           # YAML config
rich>=13.0.0          # Beautiful CLI
click>=8.1.0          # CLI framework
jinja2>=3.1.0         # HTML templates
```

### Development
```
# requirements-dev.txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.0.0
pylint>=2.17.0
mypy>=1.4.0
```

## Key Improvements

### Performance
- **Async/await**: 10x faster untuk multiple targets
- **Connection pooling**: Reuse connections
- **Concurrent scanning**: Parallel port scanning

### Reliability
- **Retry logic**: Auto-retry pada network errors
- **Timeout handling**: Proper timeout di semua level
- **Error recovery**: Graceful degradation

### Usability
- **Beautiful CLI**: Rich formatting, progress bars
- **Multiple formats**: JSON, CSV, HTML
- **Config files**: Easy batch testing
- **CI/CD ready**: Exit codes, machine-readable output

### Security
- **Allowlist enforcement**: Prevent misuse
- **Rate limiting**: Built-in rate limiting
- **Audit logging**: Track all scans
- **Credential management**: Secure API key storage

### Extensibility
- **Plugin system**: Easy to extend
- **Custom analyzers**: Add custom logic
- **Output handlers**: New output formats
- **Notification integrations**: Slack, Discord, etc

## Roadmap

### Phase 1: Core (Week 1-2)
- ✅ CLI interface with argparse
- ✅ Async scanner implementation
- ✅ JSON/CSV output
- ✅ Basic HTML report

### Phase 2: Advanced Features (Week 3-4)
- ✅ Configuration file support
- ✅ Multiple target scanning
- ✅ Scoring system
- ✅ Advanced HTML reports

### Phase 3: Integration (Week 5-6)
- ✅ Plugin system
- ✅ Slack/Discord notifications
- ✅ CI/CD integration
- ✅ Docker support

### Phase 4: Enterprise (Week 7-8)
- ✅ Prometheus metrics
- ✅ Database storage
- ✅ Web dashboard
- ✅ API server

## Success Metrics

- **Performance**: Scan 100 targets in < 5 minutes
- **Accuracy**: 99% accurate vulnerability detection
- **Usability**: < 5 minutes to first scan
- **Reliability**: 99.9% uptime in production
- **Adoption**: 1000+ GitHub stars in 6 months
