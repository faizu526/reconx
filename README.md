# ReconX v3

> **Stealth Recon & Intelligence Engine** — Protocol-aware fingerprinting, adaptive jitter, auto-correlation, and self-contained HTML reporting.

```
  ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗██╗  ██╗
  ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║╚██╗██╔╝
  ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║ ╚███╔╝
  ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║ ██╔██╗
  ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║██╔╝ ██╗
  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝
  v3.0 — Stealth Recon & Fingerprinting Engine
```

**Built by [Faizan](https://github.com/faizu526)**

---

## ⚠️ Legal Notice

> Use ReconX **only on systems you own or have explicit written authorization to test.**
> Unauthorized scanning is illegal in most jurisdictions.
> The author accepts no liability for misuse.

---

## Features

| Module | Description |
|--------|-------------|
| **Auto Recon** | Full chain: DNS → WHOIS → Geo → TLS → Robots → CT Subdomains → Headers → Proxy → Body Analysis → Port Scan → Crawl → Cross-correlation → HTML Report |
| **Port Scanner** | ThreadPool-based, adaptive worker scaling (200–1000), errno-aware OPEN/FILTERED/CLOSED classification, full-range 65k sweep support |
| **Protocol Banner Grabber** | Per-port probe payloads (FTP/SSH/SMTP/Redis/MySQL/Postgres/Mongo/Elasticsearch/Jupyter…) — not a generic HTTP probe |
| **Web Crawler** | Multi-threaded, domain-scoped, hidden content extraction (comments, secrets, internal IPs, sourcemaps, JWT patterns) |
| **Header Intelligence** | Stack fingerprint + missing security headers + header probe phase (XFF, Host, method override) + confidence scoring |
| **TLS Cert Enumerator** | SANs extraction, expiry/self-signed/weak-cipher flags, interesting internal subdomain flagging |
| **CT Subdomain Enum** | crt.sh CT log query — zero bruteforce, DNS-confirm each result, ghost vs confirmed split |
| **Reverse Proxy Detector** | Multi-signal (Via/X-Cache headers, ETag mismatch, timing delta, IP vs hostname body diff, cert CN mismatch) |
| **Deep Response Analyzer** | Framework fingerprint (React/Next/Vue/Django/Rails/WP…), error leak detection, JSON key exposure, inline client-state blobs |
| **Dork Generator** | 35+ Google/Bing dork templates for the target domain (file exposure, admin panels, API endpoints, cloud buckets) |
| **Auto-Correlation Engine** | Cross-validates findings across all modules, upgrades confidence based on corroboration count, composite signal rules |
| **HTML Report** | Self-contained, offline-ready report with risk score, findings tables by confidence, port/subdomain maps, raw JSON collapse |
| **Jitter Engine** | Three modes — `silent` (IDS-evasion), `normal`, `fast` — with per-request and burst delays |
| **GUI** | Tkinter dark-theme desktop interface, live terminal feed, tabbed Findings/Ports/Subdomains/JSON views |

---

## Installation

### Prerequisites

- Python 3.9+
- `pip`

### Clone & Install

```bash
git clone https://github.com/faizu526/reconx.git
cd reconx
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**tkinter** (GUI only) — included in most Python installs. If missing:

```bash
# Ubuntu/Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

---

## Usage

### CLI — Interactive Menu

```bash
python3 reconx_v3.py
```

Select a module (0–15), enter target and port range, pick jitter mode.

### CLI — Module Quick Reference

| Choice | Module |
|--------|--------|
| `0` | ★ **Auto Recon** (full chain + HTML report) — *start here* |
| `1` | Full Recon (manual, no auto-correlation) |
| `2` | Port Scan |
| `3` | Web Crawl |
| `4` | Crawl + Scan |
| `5` | Batch Scan from crawl JSON |
| `6` | WHOIS Lookup |
| `7` | DNS Lookup |
| `8` | IP Geolocation |
| `9` | TLS Cert Enum |
| `10` | Robots + Sitemap Harvest |
| `11` | CT Subdomain Enum |
| `12` | Dork Generator |
| `13` | Header Intelligence |
| `14` | Reverse Proxy Detect |
| `15` | Deep Response Analyze |

### Port Input Syntax

| Input | Scans |
|-------|-------|
| *(empty)* | 1–1024 |
| `common` | ~150 curated ports |
| `all` | 1–65535 |
| `80,443,8080` | Comma list |
| `1-9999` | Range |
| `80,443,8000-9000,27017` | Mixed |

### GUI

```bash
python3 reconx_gui.py
```

Dark-theme desktop app. Enter target, pick module from sidebar, watch live terminal output. Results auto-populate in Findings / Ports / Subdomains / Raw JSON tabs.

---

## Output

All output lands in `recon_output/` (gitignored):

```
recon_output/
├── report_example_com_20240101_120000.html   # Self-contained HTML report
├── auto_example_com.json                     # Full master JSON
└── ...
```

HTML report includes:
- Risk score badge (LOW / MEDIUM / HIGH / CRITICAL)
- Findings table segmented by confidence (HIGH / MEDIUM / LOW)
- Open ports table with TLS and version info
- Subdomain map with status flags
- Collapsible raw JSON panel

---

## Architecture

```
reconx_v3.py          ← Engine (all modules, no GUI deps)
reconx_gui.py         ← Tkinter frontend (monkey-patches engine.log/section)
recon_output/         ← Gitignored scan artifacts
requirements.txt
```

The GUI is a thin wrapper — it monkey-patches `engine.log` and `engine.section` to route output to the terminal widget via a thread-safe queue. All logic lives in `reconx_v3.py` and runs identically in CLI mode.

---

## Module Detail

### Jitter Engine

Three profiles control inter-request delay and burst pause:

| Mode | Request delay | Burst pause | Use case |
|------|--------------|-------------|----------|
| `silent` | 0.5–2.0s | 0.05–0.3s | IDS evasion, low-noise |
| `normal` | 0.1–0.5s | 0.01–0.1s | Default balanced |
| `fast` | 0s | 0s | Noisy, max throughput |

### Auto-Correlation Confidence Rules

- 1 source → `LOW`
- 2 sources → `MEDIUM`
- 3+ sources → `HIGH`

Composite signals (upgrade to HIGH regardless):
- Debug header + error leak on same host → dev environment exposed
- Self-signed cert + admin port open → internal tool on internet
- Missing HSTS + proxy detected → HTTPS stripping risk path

### Port Scanner — errno Classification

```
errno 0               → OPEN
ECONNREFUSED (111/61) → CLOSED
ETIMEDOUT (110)       → FILTERED
EHOSTUNREACH (113)    → FILTERED
EPERM (1)             → FILTERED (firewall drop)
```

Worker auto-scaling: ≤500 ports → 200 workers, ≤5000 → 500, ≤65535 → 1000 + chunked in 5000-port batches to prevent fd exhaustion.

---

## Author

**Faizan** — [@faizu526](https://github.com/faizu526)

---

## License

MIT — see [LICENSE](LICENSE)
