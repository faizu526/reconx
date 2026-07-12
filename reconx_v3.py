#!/usr/bin/env python3
"""
ReconX v3.0 — Advanced Recon & Intelligence Engine
Protocol-aware fingerprinting | Adaptive jitter | Stealth-first design
"""

import socket
import threading
import time
import json
import re
import random
import struct
import ssl
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════
#  COLOUR PALETTE
# ═══════════════════════════════════════════════════════════════
C = {
    'R': "\033[91m", 'G': "\033[92m", 'Y': "\033[93m",
    'B': "\033[94m", 'M': "\033[95m", 'C': "\033[96m",
    'W': "\033[97m", 'DIM': "\033[2m", 'RST': "\033[0m"
}

def banner():
    print(f"""
{C['C']}
  ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗██╗  ██╗
  ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║╚██╗██╔╝
  ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║ ╚███╔╝
  ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║ ██╔██╗
  ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║██╔╝ ██╗
  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝
{C['RST']}  {C['DIM']}v3.0 — Stealth Recon & Fingerprinting Engine{C['RST']}
  {C['DIM']}Built by {C['RST']}{C['B']}Faizan{C['RST']} {C['DIM']}· github.com/faizu526{C['RST']}
""")

def log(tag, msg, color=None):
    color = color or C['W']
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  {C['DIM']}[{ts}]{C['RST']} {color}[{tag}]{C['RST']} {msg}")

def section(title):
    print(f"\n  {C['DIM']}{'─'*50}{C['RST']}")
    print(f"  {C['W']}{title}{C['RST']}")

# ═══════════════════════════════════════════════════════════════
#  USER-AGENT ROTATION POOL
#  Real browser UAs — cycled per request to break fingerprint
# ═══════════════════════════════════════════════════════════════
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "python-requests/2.31.0",   # Occasionally blend in as legit tooling
    "curl/8.7.1",
]

def get_ua():
    return random.choice(UA_POOL)

# ═══════════════════════════════════════════════════════════════
#  JITTER ENGINE
#  Adaptive delay — mimics human / tool timing
# ═══════════════════════════════════════════════════════════════
class JitterEngine:
    """
    Three modes:
      SILENT  — long bursts, human-like pauses
      NORMAL  — moderate delay, balanced throughput
      FAST    — minimal delay, max threads (noisy but quick)
    """
    profiles = {
        "silent": (0.5,  2.0,  0.05, 0.3),   # (min_req, max_req, min_burst, max_burst)
        "normal": (0.1,  0.5,  0.01, 0.1),
        "fast":   (0.0,  0.05, 0.0,  0.01),
    }

    def __init__(self, mode="normal"):
        self.mode = mode
        self.req_min, self.req_max, self.burst_min, self.burst_max = self.profiles[mode]

    def sleep_request(self):
        if self.mode == "fast": return
        time.sleep(random.uniform(self.req_min, self.req_max))

    def sleep_burst(self):
        if self.mode == "fast": return
        time.sleep(random.uniform(self.burst_min, self.burst_max))

# ═══════════════════════════════════════════════════════════════
#  MODULE 1 — DNS Resolution (multi-level)
# ═══════════════════════════════════════════════════════════════
def resolve(target):
    target = target.replace("https://","").replace("http://","").split("/")[0]
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target):
        return target, target
    try:
        # getaddrinfo — full resolution including CNAME chain
        results = socket.getaddrinfo(target, None, socket.AF_UNSPEC)
        ipv4 = [r[4][0] for r in results if r[0] == socket.AF_INET]
        ipv6 = [r[4][0] for r in results if r[0] == socket.AF_INET6]
        ip = ipv4[0] if ipv4 else (ipv6[0] if ipv6 else None)
        if ip:
            log("DNS", f"{target} → {ip}" + (f"  (also IPv6: {ipv6[0]})" if ipv6 else ""), C['G'])
            return target, ip
    except socket.gaierror:
        pass
    log("DNS", f"Failed to resolve: {target}", C['R'])
    return None, None

# ═══════════════════════════════════════════════════════════════
#  MODULE 2 — PROTOCOL-AWARE BANNER GRABBER + FINGERPRINTER
#
#  Key upgrade from v2: Each service has its own probe payload.
#  Sending HTTP HEAD to Redis/FTP/SMTP is wrong — this fixes it.
#  Fingerprint patterns match against known signatures.
# ═══════════════════════════════════════════════════════════════

# Probes: (bytes_to_send, recv_size, wait_before_recv_ms)
# None payload = passive grab (service sends first, e.g. FTP/SSH/SMTP)
PROTOCOL_PROBES = {
    # Passive banners — service speaks first
    21:   (None,                           512,  300),   # FTP
    22:   (None,                           256,  300),   # SSH
    23:   (None,                           256,  400),   # Telnet
    25:   (None,                           512,  300),   # SMTP
    110:  (None,                           256,  300),   # POP3
    143:  (None,                           256,  300),   # IMAP
    # Active probes — we speak first
    80:   (b"HEAD / HTTP/1.1\r\nHost: TARGET\r\nConnection: close\r\n\r\n", 2048, 100),
    443:  (b"HEAD / HTTP/1.1\r\nHost: TARGET\r\nConnection: close\r\n\r\n", 2048, 100),
    8080: (b"HEAD / HTTP/1.1\r\nHost: TARGET\r\nConnection: close\r\n\r\n", 2048, 100),
    8443: (b"HEAD / HTTP/1.1\r\nHost: TARGET\r\nConnection: close\r\n\r\n", 2048, 100),
    8888: (b"GET / HTTP/1.1\r\nHost: TARGET\r\nConnection: close\r\n\r\n",  4096, 150),  # Jupyter
    # DB probes
    3306: (b"\x0e\x00\x00\x00\x0a",       128,  200),   # MySQL — partial handshake trigger
    5432: (b"\x00\x00\x00\x08\x04\xd2\x16\x2f", 128, 200),  # PostgreSQL SSL-request
    6379: (b"*1\r\n$4\r\nPING\r\n",        64,  100),   # Redis RESP PING
    27017:(b"\x3a\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\xd4\x07"
           b"\x00\x00\x00\x00\x00\x00admin.$cmd\x00\x00\x00"
           b"\x00\x00\xff\xff\xff\xff\x13\x00\x00\x00\x10isMaster"
           b"\x00\x01\x00\x00\x00\x00", 256, 200),       # MongoDB isMaster
    9200: (b"GET / HTTP/1.0\r\n\r\n",      1024, 150),   # Elasticsearch
    5984: (b"GET / HTTP/1.0\r\n\r\n",      1024, 150),   # CouchDB
    1433: (b"\x12\x01\x00\x2f\x00\x00\x01\x00"  # MSSQL pre-login
           b"\x00\x00\x1a\x00\x06\x01\x00\x20"
           b"\x00\x01\x02\x00\x21\x00\x01\x03"
           b"\x00\x22\x00\x04\xff\x08\x00\x01"
           b"\x55\x00\x00\x00",             256, 300),
    # Default HTTP for unknown HTTP ports
    "http_generic": (b"HEAD / HTTP/1.0\r\n\r\n", 1024, 100),
}

# Fingerprint signature table — (regex_pattern, service_label)
FINGERPRINTS = [
    # SSH
    (r"SSH-(\d+\.\d+)-([^\r\n]+)",              "SSH",          lambda m: f"SSH {m.group(1)} | {m.group(2).strip()}"),
    # HTTP servers
    (r"Server:\s*([^\r\n]+)",                   "HTTP",         lambda m: f"HTTP/{m.group(1).strip()}"),
    (r"X-Powered-By:\s*([^\r\n]+)",             "HTTP",         lambda m: f"Powered: {m.group(1).strip()}"),
    # FTP
    (r"^220[- ]([^\r\n]+)",                     "FTP",          lambda m: f"FTP {m.group(1).strip()}"),
    # SMTP
    (r"^220[- ]([^\r\n]+SMTP[^\r\n]*)",         "SMTP",         lambda m: f"SMTP {m.group(1).strip()}"),
    # Redis
    (r"\+PONG",                                 "Redis",        lambda m: "Redis (auth disabled)"),
    (r"-NOAUTH|WRONGPASS",                      "Redis",        lambda m: "Redis (auth required)"),
    # MySQL
    (r"[\x00-\xff]{4}\x0a([\x20-\x7e]{3,})",   "MySQL",        lambda m: f"MySQL {m.group(1)[:30]}"),
    # PostgreSQL
    (r"^N",                                     "PostgreSQL",   lambda m: "PostgreSQL (TLS refused — SSL not configured)"),
    (r"^S",                                     "PostgreSQL",   lambda m: "PostgreSQL (TLS accepted)"),
    # Elasticsearch
    (r'"number"\s*:\s*"([^"]+)"',               "Elasticsearch",lambda m: f"Elasticsearch {m.group(1)}"),
    # CouchDB
    (r'"couchdb"\s*:\s*"([^"]+)"',              "CouchDB",      lambda m: f"CouchDB {m.group(1)}"),
    (r'"version"\s*:\s*"([^"]+)"',              "CouchDB",      lambda m: f"Version {m.group(1)}"),
    # MongoDB
    (r'"ismaster"\s*:\s*1|"ismaster"\s*:\s*true',"MongoDB",     lambda m: "MongoDB (primary)"),
    # Telnet
    (r"\xff[\xfb-\xfe].",                       "Telnet",       lambda m: "Telnet IAC negotiation"),
    # Jupyter
    (r"Jupyter",                                "Jupyter",      lambda m: "Jupyter Notebook (unauthenticated check)"),
    # Generic version
    (r"(?:version|ver)[\s:/]+(\d+[\.\d]+)",     "Generic",      lambda m: f"Version {m.group(1)}"),
]

def tls_wrap(sock, host, port):
    """Upgrade to TLS — used for 443/8443 and any port that advertises TLS."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        return ctx.wrap_socket(sock, server_hostname=host), True
    except ssl.SSLError:
        return sock, False

def fingerprint_banner(raw: str, port: int) -> dict:
    """
    Run raw banner through fingerprint table.
    Returns {service, version, raw} dict.
    """
    for pattern, service, formatter in FINGERPRINTS:
        try:
            m = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
            if m:
                return {
                    "service": service,
                    "version": formatter(m)[:80],
                    "raw":     raw[:120]
                }
        except Exception:
            continue
    # Fallback — return raw if no pattern matched
    return {
        "service": "unknown",
        "version": raw[:80].strip() if raw.strip() else "",
        "raw":     raw[:120]
    }

def grab_banner_proto(ip: str, port: int, host: str, timeout: float = 2.0) -> dict:
    """
    Protocol-aware banner grab.
    1. Connect
    2. TLS upgrade if needed (443/8443)
    3. Send appropriate probe (or wait for passive banner)
    4. Read response
    5. Fingerprint
    """
    probe_data = PROTOCOL_PROBES.get(port)
    if probe_data is None:
        probe_data = PROTOCOL_PROBES["http_generic"]

    payload, recv_size, wait_ms = probe_data

    # Inject target host into HTTP probes
    if payload and b"TARGET" in payload:
        payload = payload.replace(b"TARGET", host.encode())

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))

        # TLS for known HTTPS ports
        tls_used = False
        if port in (443, 8443):
            sock, tls_used = tls_wrap(sock, host, port)

        # Passive protocol — wait for server banner
        if payload is None:
            time.sleep(wait_ms / 1000)
            raw = sock.recv(recv_size).decode(errors="ignore")
        else:
            sock.send(payload)
            time.sleep(wait_ms / 1000)
            raw = sock.recv(recv_size).decode(errors="ignore")

        sock.close()
        fp = fingerprint_banner(raw, port)
        fp["tls"] = tls_used
        return fp

    except (socket.timeout, ConnectionRefusedError, OSError):
        return {"service": "unknown", "version": "", "raw": "", "tls": False}
    except Exception:
        return {"service": "unknown", "version": "", "raw": "", "tls": False}

# ═══════════════════════════════════════════════════════════════
#  MODULE 3 — PORT SCANNER (ThreadPoolExecutor + rate control)
# ═══════════════════════════════════════════════════════════════
SERVICES = {
    21:"FTP", 22:"SSH", 23:"Telnet", 25:"SMTP", 53:"DNS",
    80:"HTTP", 110:"POP3", 143:"IMAP", 443:"HTTPS", 445:"SMB",
    1433:"MSSQL", 3306:"MySQL", 3389:"RDP", 5432:"PostgreSQL",
    5984:"CouchDB", 6379:"Redis", 8080:"HTTP-alt", 8443:"HTTPS-alt",
    8888:"Jupyter", 9200:"Elasticsearch", 27017:"MongoDB",
    902:"VMware", 912:"VMware-auth", 4848:"GlassFish",
    7001:"WebLogic", 7002:"WebLogic-TLS", 9000:"PHP-FPM",
    11211:"Memcached", 2375:"Docker-API", 2376:"Docker-TLS",
}

def scan_port(ip: str, port: int, host: str, jitter: JitterEngine,
              timeout: float = 1.5, do_fingerprint: bool = True) -> dict:
    """
    errno cross-reference (connect_ex return codes):
      0           = OPEN
      ECONNREFUSED: Linux=111, Windows=10061, macOS=61  → CLOSED (hard reset)
      ETIMEDOUT:   Linux=110, Windows=10060             → FILTERED (no response)
      EAGAIN:      Linux=11,  macOS=35, Windows=10035   → FILTERED (resource limit)
      EHOSTUNREACH:Linux=113, Windows=10065             → FILTERED (no route)
      ENETUNREACH: Linux=101, Windows=10051             → FILTERED
      EPERM:       Linux=1                              → FILTERED (firewall drop)
    Anything else → CLOSED (safe default, avoids false FILTERED)
    """
    # Platform-aware errno sets
    _FILTERED = {11, 35, 110, 113, 101, 1,          # Linux / macOS
                 10035, 10060, 10065, 10051,          # Windows
                 60, 65}                              # macOS extras
    _CLOSED   = {111, 61, 10061}                      # hard RST

    jitter.sleep_burst()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        errno = sock.connect_ex((ip, port))
        sock.close()
    except OSError:
        # Socket creation failed (fd exhaustion on very large scans) — retry once
        time.sleep(0.05)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            errno = sock.connect_ex((ip, port))
            sock.close()
        except OSError:
            return {"port": port, "status": "ERROR"}

    if errno == 0:
        fp = {}
        if do_fingerprint:
            fp = grab_banner_proto(ip, port, host, timeout=timeout)
        return {
            "port":    port,
            "status":  "OPEN",
            "service": fp.get("service") or SERVICES.get(port, "unknown"),
            "version": fp.get("version", ""),
            "tls":     fp.get("tls", False),
            "raw":     fp.get("raw", ""),
        }
    elif errno in _FILTERED:
        return {"port": port, "status": "FILTERED"}
    else:
        # CLOSED or unknown errno — treat as closed (anti-FP)
        return {"port": port, "status": "CLOSED"}

def run_scan(ip: str, ports: list, host: str, jitter: JitterEngine,
             max_workers: int = None, do_fingerprint: bool = True) -> tuple:
    """
    Adaptive worker scaling:
      ≤500 ports   → 200 workers
      ≤5000 ports  → 500 workers
      ≤65535 ports → 1000 workers, chunked in batches of 5000
    Chunking prevents fd exhaustion on full 65k sweeps.
    Exception-safe: crashed threads logged, never silently dropped.
    """
    total = len(ports)

    # Auto-scale workers
    if max_workers is None:
        if total <= 500:
            max_workers = 200
        elif total <= 5000:
            max_workers = 500
        else:
            max_workers = 1000

    section("PORT SCAN + FINGERPRINT")
    log("INFO",
        f"Target: {ip}  Ports: {total}  Workers: {max_workers}  "
        f"Mode: {jitter.mode.upper()}",
        C['C'])

    open_ports, filtered = [], []
    errors = []
    lock   = threading.Lock()
    t0     = datetime.now()
    done   = 0

    # Chunk large scans to avoid fd exhaustion
    CHUNK = 5000
    chunks = [ports[i:i+CHUNK] for i in range(0, total, CHUNK)]
    if len(chunks) > 1:
        log("INFO", f"Large scan — split into {len(chunks)} chunks of ≤{CHUNK}", C['Y'])

    for chunk_idx, chunk in enumerate(chunks):
        if len(chunks) > 1:
            log("CHUNK", f"{chunk_idx+1}/{len(chunks)}  ports {chunk[0]}–{chunk[-1]}", C['DIM'])

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(scan_port, ip, p, host, jitter,
                            do_fingerprint=do_fingerprint): p
                for p in chunk
            }
            for future in as_completed(futures):
                port_num = futures[future]
                try:
                    r = future.result()
                except Exception as exc:
                    with lock:
                        errors.append({"port": port_num, "err": str(exc)})
                    continue

                with lock:
                    done += 1
                    if r["status"] == "OPEN":
                        open_ports.append(r)
                        tls_flag = " [TLS]" if r.get("tls") else ""
                        ver = (f"  {C['DIM']}{r['version'][:60]}{C['RST']}"
                               if r.get("version") else "")
                        log("OPEN",
                            f"{r['port']:<6} {r['service']:<16}{tls_flag}{ver}",
                            C['G'])
                    elif r["status"] == "FILTERED":
                        filtered.append(r["port"])
                    elif r["status"] == "ERROR":
                        errors.append({"port": port_num, "err": "socket_error"})

        # Brief pause between chunks — OS socket table recovery
        if chunk_idx < len(chunks) - 1:
            time.sleep(0.3)

    open_ports.sort(key=lambda x: x["port"])
    elapsed = datetime.now() - t0

    log("DONE",
        f"{len(open_ports)} open | {len(filtered)} filtered | "
        f"{len(errors)} errors | {elapsed}",
        C['C'])

    if errors:
        log("ERRORS", f"{len(errors)} ports had socket errors (fd limit or timeout)", C['Y'])

    return open_ports, filtered

# ═══════════════════════════════════════════════════════════════
#  MODULE 4 — WEB CRAWLER + HIDDEN CONTENT EXTRACTOR
# ═══════════════════════════════════════════════════════════════
API_PATTERNS = [
    "/api/", "/v1/", "/v2/", "/v3/", "/graphql", "/rest/",
    "/admin", "/login", "/upload", "/backup", "/dashboard",
    "/config", "/debug", "/wp-admin", "/wp-json", "/.env",
    "/.git", "/swagger", "/openapi", "/actuator", "/metrics",
    "/health", "/status", "/console", "/manage", "/phpmyadmin",
    "/.DS_Store", "/.htaccess", "/server-status", "/info.php",
]

SENSITIVE_KEYWORDS = [
    "password", "passwd", "secret", "api_key", "token",
    "private_key", "access_key", "auth", "credential",
    "jwt", "bearer", "admin", "config", "database",
    "aws_secret", "private", "internal", "debug", "oauth",
    "refresh_token", "client_secret", "encryption_key",
]

# Regex for common secret patterns
SECRET_PATTERNS = [
    (r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']([A-Za-z0-9_\-]{20,})["\']',     "API_KEY"),
    (r'(?:secret|token)\s*[=:]\s*["\']([A-Za-z0-9_\-\.]{20,})["\']',          "SECRET_TOKEN"),
    (r'(?:password|passwd|pwd)\s*[=:]\s*["\']([^"\']{6,})["\']',               "PASSWORD"),
    (r'(?:aws_access_key_id|aws_secret_access_key)\s*[=:]\s*["\']([^"\']+)["\']', "AWS_KEY"),
    (r'(?:eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+)',    "JWT_TOKEN"),
    (r'(?:BEGIN (?:RSA |EC |DSA )?PRIVATE KEY)',                                 "PRIVATE_KEY"),
    (r'ghp_[A-Za-z0-9]{36}',                                                    "GITHUB_TOKEN"),
    (r'sk-[A-Za-z0-9]{48}',                                                     "OPENAI_KEY"),
    (r'xoxb-[0-9]{11}-[0-9]{11}-[A-Za-z0-9]{24}',                              "SLACK_BOT_TOKEN"),
]

def extract_hidden(html: str, url: str) -> list:
    findings = []

    # HTML comment secrets
    comments = re.findall(r'<!--(.*?)-->', html, re.DOTALL)
    for c in comments:
        if any(k in c.lower() for k in SENSITIVE_KEYWORDS):
            findings.append({"type": "comment_secret", "data": c.strip()[:120]})

    # Pattern-matched secrets
    for pattern, label in SECRET_PATTERNS:
        matches = re.findall(pattern, html, re.I | re.DOTALL)
        if matches:
            findings.append({"type": label, "data": [m[:80] for m in matches[:3]]})

    # Exposed emails
    emails = list(set(re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w{2,}', html)))
    internal_only = [e for e in emails if not e.endswith(('.png','.jpg','.gif','.svg'))]
    if internal_only:
        findings.append({"type": "emails", "data": internal_only[:10]})

    # RFC-1918 internal IPs
    ips = re.findall(r'\b(?:192\.168|10\.|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+\b', html)
    if ips:
        findings.append({"type": "internal_ips", "data": list(set(ips))})

    # Version disclosures
    versions = re.findall(r'(?:v|version)["\s:/]+(\d+\.\d+[\.\d]*)', html, re.I)
    if versions:
        findings.append({"type": "versions", "data": list(set(versions))[:10]})

    # Hidden / interesting paths
    paths = re.findall(r'(?:href|src|action)["\s=]+["\']([/][^"\'<>\s]{3,})["\']', html)
    interesting = [p for p in set(paths) if any(a in p.lower() for a in API_PATTERNS)]
    if interesting:
        findings.append({"type": "hidden_paths", "data": list(interesting)[:20]})

    # Source map disclosures (.map files)
    maps = re.findall(r'//# sourceMappingURL=([^\s]+\.map)', html)
    if maps:
        findings.append({"type": "sourcemaps", "data": maps[:5]})

    return findings

def crawl(base_url: str, max_depth: int = 2, jitter: JitterEngine = None) -> dict:
    if jitter is None:
        jitter = JitterEngine("normal")
    section(f"CRAWLER — {base_url}")
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"

    visited      = set()
    all_urls     = []
    api_found    = []
    all_findings = []
    lock         = threading.Lock()
    domain       = urlparse(base_url).netloc

    def same_domain(url):
        return urlparse(url).netloc == domain

    def get_links(url, html):
        links = set()
        soup  = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["a", "form", "script", "link"]):
            href = tag.get("href") or tag.get("action") or tag.get("src")
            if href:
                full = urljoin(url, href)
                if same_domain(full):
                    links.add(full.split("#")[0].split("?")[0])
        return links

    def do_crawl(url, depth):
        if depth > max_depth or url in visited:
            return
        with lock:
            if url in visited: return
            visited.add(url)
            all_urls.append(url)
            if any(p in url.lower() for p in API_PATTERNS):
                api_found.append(url)

        try:
            jitter.sleep_request()
            r = requests.get(
                url, timeout=6,
                headers={"User-Agent": get_ua(),
                         "Accept": "text/html,application/xhtml+xml,*/*",
                         "Accept-Language": "en-US,en;q=0.9"},
                allow_redirects=True
            )
            log("CRAWL", f"[{len(all_urls):>4}] {r.status_code} {url}", C['B'])

            findings = extract_hidden(r.text, url)
            if findings:
                with lock:
                    all_findings.append({"url": url, "findings": findings})
                log("FOUND", f"{len(findings)} item(s) @ {url}", C['Y'])

            links = get_links(url, r.text)
            with ThreadPoolExecutor(max_workers=8) as ex:
                for link in links:
                    ex.submit(do_crawl, link, depth + 1)
        except Exception:
            pass

    do_crawl(base_url, 0)
    log("DONE", f"{len(all_urls)} URLs | {len(api_found)} API endpoints | {len(all_findings)} pages with findings", C['G'])

    if api_found:
        section("API ENDPOINTS FOUND")
        for ep in api_found:
            log("API", ep, C['Y'])

    if all_findings:
        section("HIDDEN CONTENT EXTRACTED")
        for item in all_findings:
            log("URL", item["url"], C['C'])
            for f in item["findings"]:
                log(f["type"].upper(), str(f["data"])[:120], C['R'])

    return {"urls": all_urls, "api_endpoints": api_found, "findings": all_findings}

# ═══════════════════════════════════════════════════════════════
#  MODULE 5 — WHOIS
# ═══════════════════════════════════════════════════════════════
def whois_lookup(domain: str) -> dict:
    section("WHOIS LOOKUP")
    try:
        r = requests.get(
            f"https://www.whois.com/whois/{domain}",
            timeout=10, headers={"User-Agent": get_ua()}
        )
        fields = [
            ("Registrar:", "registrar"),
            ("Created Date:", "created"),
            ("Registry Expiry Date:", "expires"),
            ("Name Server:", "nameserver"),
            ("Registrant Organization:", "org"),
        ]
        result = {"domain": domain}
        for pattern, key in fields:
            if pattern in r.text:
                idx = r.text.find(pattern)
                val = r.text[idx+len(pattern): r.text.find("\n", idx)].strip()[:80]
                if val:
                    result[key] = val
                    log(key.upper(), val, C['C'])
        return result
    except Exception as e:
        log("ERR", str(e), C['R'])
        return {}

# ═══════════════════════════════════════════════════════════════
#  MODULE 6 — DNS Records
# ═══════════════════════════════════════════════════════════════
def dns_lookup(domain: str) -> dict:
    section("DNS LOOKUP")
    result = {}
    try:
        import dns.resolver
        for rtype in ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "SRV"]:
            try:
                ans = [str(r) for r in dns.resolver.resolve(domain, rtype)]
                result[rtype] = ans
                log(rtype, " | ".join(ans)[:90], C['Y'])
            except Exception:
                pass
    except ImportError:
        try:
            ip = socket.gethostbyname(domain)
            result["A"] = [ip]
            log("A", ip, C['Y'])
        except Exception:
            pass
    return result

# ═══════════════════════════════════════════════════════════════
#  MODULE 7 — IP Geolocation
# ═══════════════════════════════════════════════════════════════
def geoip(ip: str) -> dict:
    section("IP GEOLOCATION")
    try:
        r = requests.get(f"https://ipinfo.io/{ip}",
                         timeout=6, headers={"User-Agent": get_ua()})
        data = r.json()
        for k in ["ip", "city", "region", "country", "org", "loc", "timezone", "hostname"]:
            if k in data:
                log(k.upper(), data[k], C['C'])
        return data
    except Exception as e:
        log("ERR", str(e), C['R'])
        return {}

# ═══════════════════════════════════════════════════════════════
#  MODULE 8 — TLS CERTIFICATE ENUMERATOR
#
#  No injection, no probe beyond TLS handshake itself.
#  Extracts: CN, SANs (Subject Alternative Names), issuer,
#  validity window, cipher suite, expired/self-signed flags.
#  SANs are gold — often expose internal hostnames, staging
#  environments, and subdomains not in public DNS.
# ═══════════════════════════════════════════════════════════════
import ssl as _ssl
import datetime as _dt

def tls_enum(host: str, ports: list = None) -> dict:
    """
    Enumerate TLS on given host:port list.
    Default ports: 443, 8443, 8080, 993, 995, 465, 587
    """
    if ports is None:
        ports = [443, 8443, 8080, 993, 995, 465, 587]

    section(f"TLS CERTIFICATE ENUM — {host}")
    results = {}

    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode   = _ssl.CERT_NONE   # We want cert data even if invalid

    for port in ports:
        try:
            raw_sock = socket.create_connection((host, port), timeout=3)
            tls_sock = ctx.wrap_socket(raw_sock, server_hostname=host)
            cert     = tls_sock.getpeercert()
            cipher   = tls_sock.cipher()         # (name, protocol, bits)
            tls_sock.close()

            if not cert:
                continue

            # Parse SANs
            sans = []
            for field_type, value in cert.get("subjectAltName", []):
                if field_type == "DNS":
                    sans.append(value)

            # Parse CN from subject
            subject = dict(x[0] for x in cert.get("subject", []))
            issuer  = dict(x[0] for x in cert.get("issuer", []))
            cn      = subject.get("commonName", "")

            # Validity window
            not_before = _ssl.cert_time_to_seconds(cert.get("notBefore", ""))
            not_after  = _ssl.cert_time_to_seconds(cert.get("notAfter",  ""))
            now        = _dt.datetime.utcnow().timestamp()
            expired    = now > not_after
            days_left  = int((not_after - now) / 86400)

            # Self-signed check
            self_signed = (subject == issuer)

            entry = {
                "port":        port,
                "cn":          cn,
                "sans":        sans,
                "issuer":      issuer.get("organizationName", issuer.get("commonName", "")),
                "not_before":  cert.get("notBefore", ""),
                "not_after":   cert.get("notAfter", ""),
                "expired":     expired,
                "days_left":   days_left,
                "self_signed": self_signed,
                "cipher":      cipher[0] if cipher else "",
                "protocol":    cipher[1] if cipher else "",
                "bits":        cipher[2] if cipher else 0,
            }
            results[port] = entry

            # Display
            status_color = C['R'] if expired else (C['Y'] if days_left < 30 else C['G'])
            log("PORT",  f"{port}  {cipher[1] if cipher else ''}  {cipher[0] if cipher else ''}", C['C'])
            log("CN",    cn, C['W'])
            log("ISSUER",entry["issuer"], C['DIM'])
            log("EXPIRY",f"{entry['not_after']}  ({'EXPIRED' if expired else f'{days_left}d left'})", status_color)
            if self_signed:
                log("WARN", "Self-signed certificate", C['R'])

            if sans:
                log("SANs", f"{len(sans)} entries", C['Y'])
                # Show all — these are the interesting ones
                for san in sans:
                    flag = ""
                    # Flag internal / staging / dev patterns
                    if any(x in san.lower() for x in ["internal","staging","dev","test","admin","corp","intra","vpn","api"]):
                        flag = f" {C['R']}◄ INTERESTING{C['RST']}"
                    print(f"       {C['DIM']}{san}{C['RST']}{flag}")

            # Weak cipher flags
            if cipher and cipher[2] and cipher[2] < 128:
                log("WARN", f"Weak cipher strength: {cipher[2]} bits", C['R'])
            if cipher and cipher[1] in ("TLSv1", "TLSv1.1", "SSLv2", "SSLv3"):
                log("WARN", f"Deprecated protocol: {cipher[1]}", C['R'])

        except (socket.timeout, ConnectionRefusedError, OSError):
            pass   # Port closed / filtered — silent skip
        except _ssl.SSLError as e:
            log("SSL", f"Port {port}: {e.reason}", C['Y'])
        except Exception:
            pass

    if not results:
        log("INFO", "No TLS ports responded", C['DIM'])
    else:
        log("DONE", f"{len(results)} TLS port(s) enumerated", C['G'])

    return results

# ═══════════════════════════════════════════════════════════════
#  MODULE 9 — ROBOTS.TXT + SITEMAP HARVESTER
#
#  Fetches robots.txt and sitemap.xml before crawl.
#  Disallow paths are recon gold — they're exactly what the
#  site owner doesn't want indexed, i.e. admin panels, APIs,
#  backup paths. Queue them directly into crawl pipeline.
# ═══════════════════════════════════════════════════════════════
def harvest_robots_sitemap(base_url: str) -> dict:
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"

    section(f"ROBOTS + SITEMAP — {base_url}")
    found = {"disallowed": [], "allowed": [], "sitemaps": [], "sitemap_urls": []}

    # ── robots.txt ──────────────────────────────────────────────
    try:
        r = requests.get(f"{base_url}/robots.txt", timeout=5,
                         headers={"User-Agent": get_ua()})
        if r.status_code == 200:
            log("ROBOTS", f"{base_url}/robots.txt  [{r.status_code}]", C['G'])
            for line in r.text.splitlines():
                line = line.strip()
                if line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path and path != "/":
                        found["disallowed"].append(path)
                        flag = C['R'] if any(x in path.lower() for x in
                               ["admin","backup","config","debug","api","secret","private","upload"]) else C['Y']
                        log("DISALLOW", path, flag)
                elif line.lower().startswith("allow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        found["allowed"].append(path)
                elif line.lower().startswith("sitemap:"):
                    sm = line.split(":", 1)[1].strip()
                    found["sitemaps"].append(sm)
                    log("SITEMAP", sm, C['C'])
        else:
            log("ROBOTS", f"HTTP {r.status_code}", C['DIM'])
    except Exception:
        log("ROBOTS", "Not accessible", C['DIM'])

    # ── sitemap.xml (explicit + discovered) ──────────────────────
    sitemap_queue = found["sitemaps"] or [f"{base_url}/sitemap.xml", f"{base_url}/sitemap_index.xml"]
    visited_sitemaps = set()

    def parse_sitemap(url):
        if url in visited_sitemaps: return
        visited_sitemaps.add(url)
        try:
            r = requests.get(url, timeout=5, headers={"User-Agent": get_ua()})
            if r.status_code != 200: return
            # Nested sitemapindex
            nested = re.findall(r'<loc>\s*(https?://[^<]+sitemap[^<]*\.xml[^<]*)\s*</loc>', r.text, re.I)
            for n in nested:
                parse_sitemap(n.strip())
            # Regular URLs
            urls = re.findall(r'<loc>\s*(https?://[^\s<]+)\s*</loc>', r.text)
            clean = [u.strip() for u in urls if "sitemap" not in u.lower()]
            found["sitemap_urls"].extend(clean)
            if clean:
                log("SITEMAP", f"{len(clean)} URLs from {url}", C['G'])
        except Exception:
            pass

    for sm in sitemap_queue:
        parse_sitemap(sm)

    # Dedupe
    found["sitemap_urls"] = list(dict.fromkeys(found["sitemap_urls"]))

    log("DONE",
        f"{len(found['disallowed'])} disallowed | "
        f"{len(found['sitemap_urls'])} sitemap URLs",
        C['C'])
    return found

# ═══════════════════════════════════════════════════════════════
#  MODULE 10 — CERTIFICATE TRANSPARENCY SUBDOMAIN ENUM
#
#  crt.sh public CT logs se subdomains — zero bruteforce.
#  Discovered subdomains DNS resolve hote hain to confirm.
#  Wildcard entries filter hoti hain, sirf real hosts nikalta.
#  Confidence: DNS resolution = confirmed, no-resolve = ghost.
# ═══════════════════════════════════════════════════════════════
def ct_subdomain_enum(domain: str) -> dict:
    section(f"CT LOG SUBDOMAIN ENUM — {domain}")
    found     = {"confirmed": [], "ghost": [], "interesting": []}
    raw_names = set()

    # crt.sh JSON API — public CT log aggregator
    endpoints = [
        f"https://crt.sh/?q=%.{domain}&output=json",
        f"https://crt.sh/?q=%.%.{domain}&output=json",   # second-level wildcards
    ]

    for url in endpoints:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": get_ua()})
            if r.status_code != 200:
                continue
            entries = r.json()
            for entry in entries:
                name = entry.get("name_value", "")
                for n in name.splitlines():
                    n = n.strip().lstrip("*.")
                    if n.endswith(f".{domain}") or n == domain:
                        raw_names.add(n.lower())
        except Exception:
            continue

    log("CT", f"{len(raw_names)} unique names from CT logs", C['C'])

    # DNS resolve each — confirm real vs ghost
    INTERESTING = ["admin","api","dev","staging","test","vpn","internal",
                   "corp","intra","mail","smtp","ftp","sftp","ssh","jenkins",
                   "jira","gitlab","grafana","kibana","elastic","mongo","redis",
                   "db","database","backup","cdn","proxy","gateway","auth","sso"]

    lock = threading.Lock()

    def resolve_sub(sub):
        try:
            ip = socket.gethostbyname(sub)
            entry = {"host": sub, "ip": ip}
            flag  = any(k in sub.lower() for k in INTERESTING)
            with lock:
                found["confirmed"].append(entry)
                if flag:
                    found["interesting"].append(entry)
            color = C['R'] if flag else C['G']
            marker = "  ◄ INTERESTING" if flag else ""
            log("CONFIRMED", f"{sub:<40} {ip}{marker}", color)
        except socket.gaierror:
            with lock:
                found["ghost"].append(sub)

    with ThreadPoolExecutor(max_workers=30) as pool:
        pool.map(resolve_sub, raw_names)

    log("DONE",
        f"{len(found['confirmed'])} confirmed | "
        f"{len(found['interesting'])} interesting | "
        f"{len(found['ghost'])} ghost",
        C['C'])
    return found

# ═══════════════════════════════════════════════════════════════
#  MODULE 11 — GOOGLE / BING DORK GENERATOR
#
#  Dork strings generate karta hai target ke liye.
#  Browser mein open karta hai — Claude search karta nahi,
#  operator khud dekhe. False positive zero — human reviews.
#  Categories: exposure, login panels, files, config, code.
# ═══════════════════════════════════════════════════════════════
import webbrowser
import urllib.parse

DORK_TEMPLATES = [
    # Sensitive file exposure
    ("site:{d} ext:env",                         "ENV file exposure"),
    ("site:{d} ext:log",                         "Log file exposure"),
    ("site:{d} ext:sql",                         "SQL dump exposure"),
    ("site:{d} ext:bak OR ext:backup",           "Backup file exposure"),
    ("site:{d} ext:xml inurl:config",            "Config XML exposure"),
    ("site:{d} ext:json inurl:config",           "Config JSON exposure"),
    ("site:{d} ext:yml OR ext:yaml",             "YAML config exposure"),
    ("site:{d} ext:php inurl:phpinfo",           "phpinfo exposure"),
    # Admin / login panels
    ("site:{d} inurl:admin",                     "Admin panel"),
    ("site:{d} inurl:login",                     "Login panel"),
    ("site:{d} inurl:dashboard",                 "Dashboard"),
    ("site:{d} inurl:wp-admin",                  "WordPress admin"),
    ("site:{d} inurl:phpmyadmin",                "phpMyAdmin"),
    ("site:{d} inurl:jenkins",                   "Jenkins"),
    ("site:{d} inurl:grafana",                   "Grafana"),
    ("site:{d} inurl:kibana",                    "Kibana"),
    # API / swagger
    ("site:{d} inurl:swagger",                   "Swagger UI"),
    ("site:{d} inurl:api-docs",                  "API docs"),
    ("site:{d} inurl:openapi",                   "OpenAPI spec"),
    ("site:{d} inurl:graphql",                   "GraphQL endpoint"),
    # Sensitive content in pages
    ("site:{d} intext:\"index of /\"",           "Directory listing"),
    ("site:{d} intext:\"DB_PASSWORD\"",          "DB creds in page"),
    ("site:{d} intext:\"api_key\"",              "API key in page"),
    ("site:{d} intext:\"BEGIN RSA PRIVATE KEY\"","Private key in page"),
    ("site:{d} intext:\"Authorization: Bearer\"","Bearer token in page"),
    # Git / source exposure
    ("site:{d} inurl:.git",                      "Git dir exposed"),
    ("site:{d} inurl:.svn",                      "SVN dir exposed"),
    # Error pages — version disclosure
    ("site:{d} intext:\"stack trace\"",          "Stack trace exposure"),
    ("site:{d} intext:\"SQL syntax\"",           "SQL error exposure"),
    ("site:{d} intext:\"Warning: mysql\"",       "MySQL error exposure"),
    # Cloud / infra
    ("site:{d} intext:\"s3.amazonaws.com\"",     "S3 bucket reference"),
    ("site:{d} intext:\"storage.googleapis.com\"","GCS bucket reference"),
    # Cached / old pages
    (f"cache:{'{d}'}",                           "Cached version"),
    ("related:{d}",                              "Related domains"),
]

def dork_generator(domain: str, auto_open: bool = False) -> list:
    section(f"DORK GENERATOR — {domain}")
    generated = []

    for template, label in DORK_TEMPLATES:
        query = template.replace("{d}", domain)
        g_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        b_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        entry = {"label": label, "query": query, "google": g_url, "bing": b_url}
        generated.append(entry)
        log("DORK", f"{label:<35} {query}", C['Y'])

    log("DONE", f"{len(generated)} dork queries generated", C['G'])

    if auto_open:
        log("INFO", "Opening top 5 in browser...", C['C'])
        for d in generated[:5]:
            webbrowser.open(d["google"])
            time.sleep(1.5)

    return generated

# ═══════════════════════════════════════════════════════════════
#  MODULE 12 — HEADER INTELLIGENCE + MANIPULATION ENGINE
#
#  Phase 1 — Passive read: stack fingerprint from response headers
#  Phase 2 — Probe: send crafted headers, observe response diff
#             (no injection, just header field manipulation)
#  Phase 3 — Score misconfigurations with confidence rating
#
#  Anti-FP: every finding needs 2+ signals to be HIGH confidence.
# ═══════════════════════════════════════════════════════════════

# Header → (stack/tech, risk_note)
HEADER_INTEL = {
    "server":              ("Web Server",      "Version disclosure"),
    "x-powered-by":        ("Backend Stack",   "Tech stack disclosure"),
    "x-aspnet-version":    ("ASP.NET",         "Framework version disclosed"),
    "x-aspnetmvc-version": ("ASP.NET MVC",     "MVC version disclosed"),
    "x-generator":         ("CMS/Framework",   "Generator disclosed"),
    "x-drupal-cache":      ("Drupal",          "CMS fingerprint"),
    "x-wp-total":          ("WordPress",       "WP API active"),
    "x-shopify-stage":     ("Shopify",         "Platform fingerprint"),
    "x-magento-vary":      ("Magento",         "Platform fingerprint"),
    "via":                 ("Proxy/CDN",       "Proxy chain visible"),
    "x-varnish":           ("Varnish Cache",   "Cache fingerprint"),
    "x-cache":             ("CDN/Cache",       "Cache layer visible"),
    "x-cache-hits":        ("CDN",             "Cache hit count exposed"),
    "x-served-by":         ("CDN Node",        "Node identity exposed"),
    "x-amz-request-id":    ("AWS",             "AWS infra confirmed"),
    "x-amz-id-2":          ("AWS S3",          "S3 bucket confirmed"),
    "x-azure-ref":         ("Azure",           "Azure infra confirmed"),
    "x-goog-resource-type":("GCP",             "GCP infra confirmed"),
    "cf-ray":              ("Cloudflare",      "Cloudflare confirmed"),
    "x-vercel-id":         ("Vercel",          "Vercel deployment"),
    "x-netlify-ip":        ("Netlify",         "Netlify deployment"),
    "x-firebase-locale":   ("Firebase",        "Firebase backend"),
}

# Security headers that SHOULD be present — absence = misconfiguration
SECURITY_HEADERS_REQUIRED = {
    "strict-transport-security": "HSTS missing — HTTPS downgrade possible",
    "content-security-policy":   "CSP missing — XSS surface open",
    "x-frame-options":           "Clickjacking protection missing",
    "x-content-type-options":    "MIME sniffing protection missing",
    "referrer-policy":           "Referrer leakage possible",
    "permissions-policy":        "Feature policy unset",
    "x-xss-protection":          "Legacy XSS filter unset (minor)",
}

# Headers that should NOT be in production
HEADERS_DANGEROUS = {
    "x-debug":             "Debug mode active",
    "x-debug-token":       "Symfony debug token exposed",
    "x-debug-token-link":  "Symfony profiler link exposed",
    "x-runtime":           "Server runtime exposed (Rails)",
    "x-rack-cache":        "Rack cache internals exposed",
    "x-request-id":        "Internal request ID exposed",
    "x-forwarded-server":  "Internal server name exposed",
    "x-original-url":      "URL rewrite internals exposed",
    "x-rewrite-url":       "URL rewrite internals exposed",
}

def header_intelligence(url: str) -> dict:
    section(f"HEADER INTELLIGENCE — {url}")
    if not url.startswith("http"):
        url = f"http://{url}"

    result = {
        "stack":       [],
        "missing_sec": [],
        "dangerous":   [],
        "raw":         {},
        "probe":       {},
        "score":       {"misconfigs": 0, "confidence": "LOW"},
    }

    # ── Phase 1: Passive read ────────────────────────────────────
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": get_ua()},
                         allow_redirects=True)
        headers_lower = {k.lower(): v for k, v in r.headers.items()}
        result["raw"] = dict(r.headers)

        # Stack fingerprint
        for hdr, (tech, note) in HEADER_INTEL.items():
            if hdr in headers_lower:
                val   = headers_lower[hdr]
                entry = {"header": hdr, "value": val, "tech": tech, "note": note}
                result["stack"].append(entry)
                log("STACK", f"{hdr}: {val[:60]}  [{tech}]", C['C'])

        # Missing security headers
        for hdr, note in SECURITY_HEADERS_REQUIRED.items():
            if hdr not in headers_lower:
                result["missing_sec"].append({"header": hdr, "note": note})
                log("MISSING", f"{hdr}  →  {note}", C['Y'])
                result["score"]["misconfigs"] += 1

        # Dangerous headers present
        for hdr, note in HEADERS_DANGEROUS.items():
            if hdr in headers_lower:
                val = headers_lower[hdr]
                result["dangerous"].append({"header": hdr, "value": val, "note": note})
                log("DANGER", f"{hdr}: {val[:60]}  →  {note}", C['R'])
                result["score"]["misconfigs"] += 2   # Weight dangerous higher

    except Exception as e:
        log("ERR", str(e), C['R'])
        return result

    # ── Phase 2: Header probing — observe response diff ─────────
    # Send unusual but legitimate headers — see if server leaks info
    probes = [
        # X-Forwarded-For manipulation — does server trust it?
        {"X-Forwarded-For": "127.0.0.1",           "_label": "XFF_loopback"},
        {"X-Forwarded-For": "192.168.1.1",          "_label": "XFF_rfc1918"},
        # Host header variation — virtual host detection
        {"Host": f"localhost",                      "_label": "host_localhost"},
        # Method override probes
        {"X-HTTP-Method-Override": "DELETE",        "_label": "method_override"},
        {"X-HTTP-Method": "PUT",                    "_label": "method_header"},
        # Content negotiation probe
        {"Accept": "application/json",              "_label": "accept_json"},
    ]

    baseline_len    = len(r.content)
    baseline_status = r.status_code

    for probe_headers in probes:
        label = probe_headers.pop("_label")
        try:
            h = {"User-Agent": get_ua(), **probe_headers}
            pr = requests.get(url, timeout=6, headers=h,
                              allow_redirects=False)
            diff_status = pr.status_code != baseline_status
            diff_len    = abs(len(pr.content) - baseline_len) > 200

            if diff_status or diff_len:
                finding = {
                    "probe":          label,
                    "sent":           probe_headers,
                    "baseline_status": baseline_status,
                    "probe_status":   pr.status_code,
                    "len_diff":       len(pr.content) - baseline_len,
                }
                result["probe"][label] = finding
                log("PROBE",
                    f"{label}  status:{baseline_status}→{pr.status_code}  "
                    f"len_diff:{finding['len_diff']:+d}",
                    C['M'])
        except Exception:
            pass

    # ── Phase 3: Confidence scoring ──────────────────────────────
    m = result["score"]["misconfigs"]
    if m >= 6:
        result["score"]["confidence"] = "HIGH"
    elif m >= 3:
        result["score"]["confidence"] = "MEDIUM"
    else:
        result["score"]["confidence"] = "LOW"

    log("SCORE",
        f"{m} misconfigs | Confidence: {result['score']['confidence']}",
        C['R'] if m >= 6 else C['Y'] if m >= 3 else C['G'])

    return result

# ═══════════════════════════════════════════════════════════════
#  MODULE 13 — REVERSE PROXY DETECTOR
#
#  Signals used (no bruteforce):
#    1. TTL analysis     — origin TTL vs CDN TTL pattern
#    2. Header leakage   — Via, X-Forwarded-*, X-Real-IP
#    3. IP ≠ cert CN     — cert issued to different host = proxy
#    4. Timing diff      — cached vs uncached response delta
#    5. ETag/Age headers — proxy cache tells its story
#    6. Status code diff — direct IP vs hostname (vhost routing)
#
#  Each signal adds confidence — 3+ signals = CONFIRMED PROXY
# ═══════════════════════════════════════════════════════════════
def reverse_proxy_detect(host: str, ip: str) -> dict:
    section(f"REVERSE PROXY DETECTION — {host}")
    signals  = []
    result   = {"proxy_detected": False, "signals": [], "proxy_type": "unknown", "confidence": 0}

    base_url     = f"http://{host}"
    base_url_ip  = f"http://{ip}"

    # Signal 1: Via / X-Forwarded headers
    try:
        r = requests.get(base_url, timeout=6, headers={"User-Agent": get_ua()},
                         allow_redirects=False)
        hdrs = {k.lower(): v for k, v in r.headers.items()}

        proxy_hdrs = ["via", "x-forwarded-for", "x-forwarded-host",
                      "x-real-ip", "x-proxy-id", "x-bluecoat-via",
                      "x-served-by", "x-cache", "x-varnish",
                      "cf-ray", "x-amz-cf-id", "x-azure-ref"]
        for ph in proxy_hdrs:
            if ph in hdrs:
                signals.append({"signal": f"header:{ph}", "value": hdrs[ph], "weight": 2})
                log("SIGNAL", f"Proxy header: {ph}: {hdrs[ph][:60]}", C['Y'])

        # Signal 2: Age header — cached response
        if "age" in hdrs:
            signals.append({"signal": "age_header", "value": hdrs["age"], "weight": 1})
            log("SIGNAL", f"Age header present: {hdrs['age']}s — cached response", C['Y'])

        # Signal 3: ETag inconsistency across requests
        etag1 = hdrs.get("etag", "")
        r2    = requests.get(base_url, timeout=6, headers={"User-Agent": get_ua()},
                             allow_redirects=False)
        hdrs2 = {k.lower(): v for k, v in r2.headers.items()}
        etag2 = hdrs2.get("etag", "")
        if etag1 and etag2 and etag1 != etag2:
            signals.append({"signal": "etag_mismatch", "value": f"{etag1} vs {etag2}", "weight": 2})
            log("SIGNAL", "ETag changes between requests — load balancer or rotating cache", C['R'])

        # Signal 4: Timing — cache hit vs forced cache miss
        t1 = time.time()
        requests.get(base_url, timeout=6, headers={
            "User-Agent": get_ua(),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        })
        t1 = time.time() - t1

        t2 = time.time()
        requests.get(base_url, timeout=6, headers={"User-Agent": get_ua()})
        t2 = time.time() - t2

        timing_delta = abs(t1 - t2)
        if timing_delta > 0.15:   # >150ms diff = likely cache serving
            signals.append({"signal": "timing_delta", "value": f"{timing_delta:.3f}s", "weight": 2})
            log("SIGNAL", f"Timing delta {timing_delta:.3f}s (no-cache vs cached) — proxy caching", C['Y'])

    except Exception:
        pass

    # Signal 5: Direct IP vs hostname — different responses = vhost routing behind proxy
    try:
        r_host = requests.get(base_url, timeout=6,
                              headers={"User-Agent": get_ua()}, allow_redirects=False)
        r_ip   = requests.get(base_url_ip, timeout=6,
                              headers={"User-Agent": get_ua(), "Host": host},
                              allow_redirects=False)
        if r_host.status_code != r_ip.status_code:
            signals.append({"signal": "ip_vs_host_status",
                            "value": f"host={r_host.status_code} ip={r_ip.status_code}",
                            "weight": 3})
            log("SIGNAL",
                f"IP direct={r_ip.status_code} vs hostname={r_host.status_code} — proxy routing",
                C['R'])
        elif abs(len(r_host.content) - len(r_ip.content)) > 500:
            signals.append({"signal": "ip_vs_host_body_diff",
                            "value": f"diff={len(r_host.content)-len(r_ip.content)}b",
                            "weight": 2})
            log("SIGNAL", "Body length differs IP vs hostname — WAF or proxy layer", C['Y'])
    except Exception:
        pass

    # Signal 6: Cert CN vs actual host
    try:
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = _ssl.CERT_NONE
        s   = socket.create_connection((host, 443), timeout=4)
        ts  = ctx.wrap_socket(s, server_hostname=host)
        cert = ts.getpeercert()
        ts.close()
        subj = dict(x[0] for x in cert.get("subject", []))
        cn   = subj.get("commonName", "")
        if cn and host not in cn and not cn.startswith("*."):
            signals.append({"signal": "cert_cn_mismatch",
                            "value": f"cert_cn={cn} host={host}", "weight": 3})
            log("SIGNAL", f"Cert CN {cn} ≠ {host} — terminating proxy or CDN", C['R'])
    except Exception:
        pass

    # Aggregate
    confidence = sum(s["weight"] for s in signals)
    result["signals"]    = signals
    result["confidence"] = confidence

    # Identify proxy type from signals
    signal_vals = " ".join(s.get("value","") for s in signals)
    if "cf-ray" in str(signals):
        result["proxy_type"] = "Cloudflare"
    elif "x-amz-cf-id" in str(signals):
        result["proxy_type"] = "AWS CloudFront"
    elif "x-azure-ref" in str(signals):
        result["proxy_type"] = "Azure Front Door"
    elif "x-varnish" in str(signals):
        result["proxy_type"] = "Varnish"
    elif "x-cache" in str(signals):
        result["proxy_type"] = "Generic CDN/Cache"
    elif confidence >= 3:
        result["proxy_type"] = "Unknown Proxy/LB"

    if confidence >= 3:
        result["proxy_detected"] = True
        log("RESULT",
            f"PROXY CONFIRMED — {result['proxy_type']} "
            f"(confidence score: {confidence})",
            C['R'])
    elif confidence >= 1:
        log("RESULT", f"Possible proxy — weak signals (score: {confidence})", C['Y'])
    else:
        log("RESULT", "No proxy detected", C['G'])

    return result

# ═══════════════════════════════════════════════════════════════
#  MODULE 14 — DEEP RESPONSE BODY ANALYZER
#
#  Full response body scan — every tag, every key, every pattern.
#  Framework: HTML5 tags, script src, meta, JSON structure,
#             React/Vue/Angular fingerprint, GraphQL hints,
#             inline credentials, internal paths, error leaks.
#
#  Anti-FP: each finding has a confidence field.
#  LOW  = single pattern match
#  MED  = 2 corroborating signals
#  HIGH = 3+ signals or unique identifier
# ═══════════════════════════════════════════════════════════════

# Script src patterns → framework fingerprint
SCRIPT_FINGERPRINTS = [
    (r'react(?:\.min)?\.js|react-dom',               "React",          "MED"),
    (r'vue(?:\.min)?\.js|__vue__',                   "Vue.js",         "MED"),
    (r'angular(?:\.min)?\.js|ng-version',            "AngularJS",      "MED"),
    (r'@angular/core|zone\.js',                      "Angular",        "MED"),
    (r'next(?:\.js)?/_next/|__NEXT_DATA__',          "Next.js",        "HIGH"),
    (r'nuxt(?:\.js)?/_nuxt/|__NUXT__',              "Nuxt.js",        "HIGH"),
    (r'svelte(?:\.min)?\.js|__svelte',               "Svelte",         "MED"),
    (r'ember(?:\.min)?\.js|Ember\.VERSION',          "Ember.js",       "MED"),
    (r'backbone(?:\.min)?\.js',                      "Backbone.js",    "LOW"),
    (r'jquery(?:\.min)?\.js|jQuery\.fn\.jquery',     "jQuery",         "LOW"),
    (r'webpack(?:\.min)?\.js|__webpack_require__',   "Webpack",        "MED"),
    (r'chunk\.[a-f0-9]+\.js|app\.[a-f0-9]+\.js',    "Webpack chunks", "LOW"),
    (r'graphql|__schema|__typename',                 "GraphQL",        "MED"),
    (r'laravel|Laravel\.js|csrf-token.*laravel',     "Laravel",        "HIGH"),
    (r'django|csrfmiddlewaretoken',                  "Django",         "HIGH"),
    (r'rails|authenticity_token|__rails__',          "Ruby on Rails",  "HIGH"),
    (r'wp-content|wp-includes|wordpress',            "WordPress",      "HIGH"),
    (r'Drupal\.settings|drupal\.js',                 "Drupal",         "HIGH"),
    (r'joomla|/media/jui/',                          "Joomla",         "HIGH"),
    (r'strapi|/uploads/',                            "Strapi CMS",     "LOW"),
    (r'socket\.io(?:\.min)?\.js',                    "Socket.IO",      "MED"),
]

# Meta tag patterns
META_INTEL = [
    (r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']',  "generator"),
    (r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)["\']',     "author"),
    (r'<meta[^>]+name=["\']application-name["\'][^>]+content=["\']([^"\']+)["\']', "app_name"),
]

# JSON key patterns in response body (API responses)
JSON_EXPOSURE_KEYS = [
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "access_key", "private_key", "auth_token", "session", "cookie",
    "credit_card", "ssn", "dob", "phone", "address", "internal_ip",
    "debug", "stack_trace", "error_message", "database_url", "db_url",
    "aws_access", "aws_secret", "stripe_key", "twilio",
]

# HTML comment / error patterns
ERROR_PATTERNS = [
    (r'(?:Fatal error|Warning|Notice):\s+(.{0,100})',    "PHP error"),
    (r'Traceback \(most recent call last\)',             "Python traceback"),
    (r'at .+\((.+\.java:\d+)\)',                         "Java stack trace"),
    (r'System\.Exception|NullReferenceException',        "C#/.NET exception"),
    (r'ORA-\d{5}',                                       "Oracle DB error"),
    (r'mysql_fetch|mysql_num_rows|You have an error in your SQL syntax', "MySQL error"),
    (r'PostgreSQL.*ERROR|PSQLException',                 "PostgreSQL error"),
    (r'Microsoft OLE DB|ODBC SQL Server',                "MSSQL/ODBC error"),
    (r'MongoError|MongoServerError',                     "MongoDB error"),
    (r'redis\.exceptions|RedisError',                    "Redis error"),
    (r'<b>Notice</b>|<b>Warning</b>|<b>Fatal error</b>','PHP error (HTML)'),
]

def deep_response_analyze(url: str) -> dict:
    section(f"DEEP RESPONSE ANALYSIS — {url}")
    if not url.startswith("http"):
        url = f"http://{url}"

    result = {
        "url":          url,
        "frameworks":   [],
        "meta":         [],
        "json_exposure":[],
        "errors":       [],
        "scripts":      [],
        "forms":        [],
        "links_offsite":[],
        "comments":     [],
        "inline_data":  [],
    }

    try:
        r = requests.get(url, timeout=10,
                         headers={"User-Agent": get_ua(),
                                  "Accept": "text/html,application/xhtml+xml,application/json,*/*"},
                         allow_redirects=True)
        body    = r.text
        ct      = r.headers.get("Content-Type", "").lower()
        is_json = "json" in ct or (body.strip().startswith("{") or body.strip().startswith("["))

    except Exception as e:
        log("ERR", str(e), C['R'])
        return result

    # ── Script src collection ────────────────────────────────────
    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', body, re.I)
    result["scripts"] = script_srcs[:30]

    # ── Framework fingerprint from entire body ───────────────────
    seen_frameworks = set()
    combined = body + " ".join(script_srcs)
    for pattern, framework, confidence in SCRIPT_FINGERPRINTS:
        if framework in seen_frameworks:
            continue
        if re.search(pattern, combined, re.I):
            seen_frameworks.add(framework)
            result["frameworks"].append({"name": framework, "confidence": confidence})
            color = C['R'] if confidence == "HIGH" else C['Y'] if confidence == "MED" else C['DIM']
            log("FRAMEWORK", f"{framework:<20} [{confidence}]", color)

    # ── Meta tags ────────────────────────────────────────────────
    for pattern, label in META_INTEL:
        m = re.search(pattern, body, re.I)
        if m:
            val = m.group(1).strip()
            result["meta"].append({"type": label, "value": val})
            log("META", f"{label}: {val}", C['C'])

    # ── Error leaks ──────────────────────────────────────────────
    for pattern, label in ERROR_PATTERNS:
        matches = re.findall(pattern, body, re.I)
        if matches:
            result["errors"].append({"type": label, "samples": [m[:100] for m in matches[:3]]})
            log("ERROR_LEAK", f"{label}  [{len(matches)} match(es)]", C['R'])

    # ── HTML comment analysis ────────────────────────────────────
    comments = re.findall(r'<!--(.*?)-->', body, re.DOTALL)
    for c in comments:
        c = c.strip()
        if len(c) < 3: continue
        # Only flag comments with substance
        if any(k in c.lower() for k in ["todo", "fixme", "hack", "password",
                                          "secret", "key", "token", "debug",
                                          "remove", "temp", "internal"]):
            result["comments"].append(c[:200])
            log("COMMENT", c[:100], C['Y'])

    # ── JSON body analysis ───────────────────────────────────────
    if is_json:
        def flatten_json(obj, prefix=""):
            """Recursively flatten JSON to key:value pairs."""
            items = {}
            if isinstance(obj, dict):
                for k, v in obj.items():
                    key = f"{prefix}.{k}" if prefix else k
                    items.update(flatten_json(v, key))
            elif isinstance(obj, list):
                for i, v in enumerate(obj[:5]):  # cap at 5 items
                    items.update(flatten_json(v, f"{prefix}[{i}]"))
            else:
                items[prefix] = str(obj)[:100]
            return items

        try:
            parsed   = r.json()
            flat     = flatten_json(parsed)
            for key, val in flat.items():
                key_lower = key.lower()
                if any(ek in key_lower for ek in JSON_EXPOSURE_KEYS):
                    result["json_exposure"].append({"key": key, "value": val[:80]})
                    log("JSON_EXPOSE", f"{key}: {val[:60]}", C['R'])
        except Exception:
            # Not valid JSON — try inline JSON in HTML (window.__STATE__ etc.)
            inline = re.findall(
                r'(?:window\.__\w+__|__INITIAL_STATE__|__REDUX_STATE__|__NEXT_DATA__'
                r'|__NUXT__|__APP_STATE__)\s*=\s*(\{.{20,5000}?\});',
                body, re.DOTALL
            )
            for blob in inline[:3]:
                result["inline_data"].append(blob[:300])
                log("INLINE_STATE", f"Client-side state object ({len(blob)}b)", C['M'])
                # Check for keys in inline state
                for ek in JSON_EXPOSURE_KEYS:
                    if re.search(rf'"{ek}"\s*:', blob, re.I):
                        log("INLINE_KEY", f"Sensitive key in client state: {ek}", C['R'])

    # ── Form analysis ────────────────────────────────────────────
    soup   = BeautifulSoup(body, "html.parser")
    forms  = soup.find_all("form")
    for form in forms:
        action  = form.get("action", "")
        method  = form.get("method", "GET").upper()
        fields  = [inp.get("name","") for inp in form.find_all(["input","textarea","select"])]
        fentry  = {"action": action, "method": method, "fields": fields}
        result["forms"].append(fentry)
        has_sensitive = any(f.lower() in ["password","passwd","token","secret","card","cvv"]
                            for f in fields if f)
        log("FORM",
            f"{method} {action[:50]}  fields:{fields[:5]}",
            C['R'] if has_sensitive else C['B'])

    # ── Off-site links ────────────────────────────────────────────
    parsed_base = urlparse(url)
    base_domain = parsed_base.netloc
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("http") and urlparse(href).netloc != base_domain:
            result["links_offsite"].append(href)

    if result["links_offsite"]:
        log("OFFSITE", f"{len(result['links_offsite'])} external links", C['DIM'])

    # ── Summary ──────────────────────────────────────────────────
    total_findings = (len(result["frameworks"]) + len(result["errors"]) +
                      len(result["json_exposure"]) + len(result["comments"]) +
                      len(result["inline_data"]))
    log("DONE",
        f"Frameworks:{len(result['frameworks'])}  "
        f"Errors:{len(result['errors'])}  "
        f"JSON_expose:{len(result['json_exposure'])}  "
        f"Comments:{len(result['comments'])}",
        C['G'])
    return result

# ═══════════════════════════════════════════════════════════════
#  MODULE 16 — AUTO-CORRELATION ENGINE
#
#  Ek target dalo — poori chain khud chale.
#  Flow:
#    1. Primary target recon (DNS/WHOIS/GEO/TLS/headers/body)
#    2. CT subdomains discover → har ek pe bhi recon chain
#    3. Open ports discover → port-specific checks
#    4. Crawl → discovered URLs pe body analysis
#    5. Sab findings ek jagah → cross-validate → confidence score
#
#  Anti-FP rules:
#    - Ek source se finding = LOW (report mein, highlight nahi)
#    - Do source se corroborate = MEDIUM
#    - Teen+ source se confirm = HIGH (top of report)
#    - Duplicate IPs across subdomains = dedupe, ek hi scan
# ═══════════════════════════════════════════════════════════════

def auto_correlate(target: str, jitter: JitterEngine, ports_input: str = "common") -> dict:
    section(f"AUTO-CORRELATION ENGINE — {target}")
    log("INFO", "Phase 1/6 — Primary target resolution", C['C'])

    master = {
        "target":      target,
        "timestamp":   datetime.now().isoformat(),
        "primary":     {},
        "subdomains":  {},
        "all_findings": [],
        "dedupe_ips":  set(),
    }

    # ── Phase 1: Primary target ──────────────────────────────────
    host, ip = resolve(target)
    if not ip:
        log("ERR", "Cannot resolve target — aborting", C['R'])
        return master

    master["primary"]["host"] = host
    master["primary"]["ip"]   = ip
    master["dedupe_ips"].add(ip)

    master["primary"]["whois"]   = whois_lookup(host)
    master["primary"]["dns"]     = dns_lookup(host)
    master["primary"]["geo"]     = geoip(ip)
    master["primary"]["tls"]     = tls_enum(host)
    master["primary"]["robots"]  = harvest_robots_sitemap(f"http://{host}")
    master["primary"]["headers"] = header_intelligence(f"http://{host}")
    master["primary"]["proxy"]   = reverse_proxy_detect(host, ip)
    master["primary"]["body"]    = deep_response_analyze(f"http://{host}")

    # ── Phase 2: CT subdomain discovery + chain ──────────────────
    log("INFO", "Phase 2/6 — CT subdomain chain", C['C'])
    ct = ct_subdomain_enum(host)
    master["primary"]["subdomains"] = ct
    confirmed_subs = ct.get("confirmed", [])

    for sub_entry in confirmed_subs:
        sub_host = sub_entry["host"]
        sub_ip   = sub_entry["ip"]

        # Dedupe — same IP already scanned? Skip port scan, still do web checks
        already_scanned_ip = sub_ip in master["dedupe_ips"]
        master["dedupe_ips"].add(sub_ip)

        log("CHAIN", f"→ {sub_host} ({sub_ip})"
            + (" [IP deduped — skipping port scan]" if already_scanned_ip else ""), C['M'])

        sub_data = {"host": sub_host, "ip": sub_ip}

        # Web-layer checks always run per subdomain (different vhost = different app)
        sub_data["headers"] = header_intelligence(f"http://{sub_host}")
        sub_data["body"]    = deep_response_analyze(f"http://{sub_host}")
        sub_data["tls"]     = tls_enum(sub_host, [443, 8443])

        # Port scan only if new IP
        if not already_scanned_ip:
            ports = parse_ports(ports_input)
            sub_data["ports"], sub_data["filtered"] = run_scan(
                sub_ip, ports, sub_host, jitter)
        else:
            sub_data["ports"]    = []
            sub_data["filtered"] = []
            sub_data["note"]     = "Port scan skipped — IP shared with already-scanned host"

        master["subdomains"][sub_host] = sub_data
        jitter.sleep_request()

    # ── Phase 3: Port scan primary ───────────────────────────────
    log("INFO", "Phase 3/6 — Primary port scan", C['C'])
    ports = parse_ports(ports_input)
    open_ports, filtered = run_scan(ip, ports, host, jitter)
    master["primary"]["ports"]    = open_ports
    master["primary"]["filtered"] = filtered

    # ── Phase 4: Crawl → per-URL body analysis ───────────────────
    log("INFO", "Phase 4/6 — Crawl + URL body analysis", C['C'])
    crawl_result = crawl(f"http://{host}", max_depth=2, jitter=jitter)
    master["primary"]["crawl"] = crawl_result

    # Analyze interesting discovered URLs
    interesting_urls = crawl_result.get("api_endpoints", [])[:10]
    url_analyses = {}
    for url in interesting_urls:
        log("CHAIN", f"→ Body analyze: {url}", C['M'])
        url_analyses[url] = deep_response_analyze(url)
        jitter.sleep_request()
    master["primary"]["url_analyses"] = url_analyses

    # ── Phase 5: Cross-correlation + confidence scoring ──────────
    log("INFO", "Phase 5/6 — Cross-correlating findings", C['C'])
    master["all_findings"] = _correlate_findings(master)

    # ── Phase 6: Clean up non-serializable ──────────────────────
    log("INFO", "Phase 6/6 — Finalising report", C['C'])
    master["dedupe_ips"] = list(master["dedupe_ips"])

    # Summary counts
    high   = [f for f in master["all_findings"] if f["confidence"] == "HIGH"]
    medium = [f for f in master["all_findings"] if f["confidence"] == "MEDIUM"]
    low    = [f for f in master["all_findings"] if f["confidence"] == "LOW"]

    section("CORRELATION SUMMARY")
    log("HIGH",   f"{len(high)}   findings", C['R'])
    log("MEDIUM", f"{len(medium)} findings", C['Y'])
    log("LOW",    f"{len(low)}   findings",  C['DIM'])
    log("SUBS",   f"{len(master['subdomains'])} subdomains chained", C['C'])

    return master


def _correlate_findings(master: dict) -> list:
    """
    Walk entire master report tree.
    Collect raw findings → group by type → score confidence.
    Confidence rules:
      1 source  → LOW
      2 sources → MEDIUM
      3+ sources → HIGH
    Also cross-checks:
      - Same port open on 3+ subdomains → HIGH (shared infra pattern)
      - Debug header + error leak same host → HIGH (dev exposure)
      - Self-signed cert + open admin port → HIGH
      - Missing HSTS + proxy detected → MEDIUM (downgrade risk)
    """
    findings = []

    def add(ftype, detail, source, confidence="LOW", evidence=None):
        findings.append({
            "type":       ftype,
            "detail":     detail,
            "source":     source,
            "confidence": confidence,
            "evidence":   evidence or [],
        })

    # ── Pull from primary ────────────────────────────────────────
    p = master.get("primary", {})

    # Headers
    hdr = p.get("headers", {})
    for item in hdr.get("dangerous", []):
        add("DANGEROUS_HEADER", item["note"],
            f"primary:{item['header']}", "HIGH", [item])
    for item in hdr.get("missing_sec", []):
        add("MISSING_SEC_HEADER", item["note"],
            f"primary:missing:{item['header']}", "MEDIUM", [item])
    for item in hdr.get("stack", []):
        add("STACK_DISCLOSURE", f"{item['tech']}: {item['value'][:60]}",
            f"primary:header:{item['header']}", "LOW", [item])
    for label, probe in hdr.get("probe", {}).items():
        add("HEADER_PROBE_DIFF", f"Server reacts to {label}",
            f"primary:probe:{label}", "MEDIUM", [probe])

    # Body analysis
    body = p.get("body", {})
    for fw in body.get("frameworks", []):
        conf = fw["confidence"]
        add("FRAMEWORK", fw["name"], "primary:body", conf, [fw])
    for err in body.get("errors", []):
        add("ERROR_LEAK", err["type"], "primary:body", "HIGH", err["samples"])
    for cmt in body.get("comments", []):
        add("HTML_COMMENT", cmt[:100], "primary:body", "MEDIUM")
    for exp in body.get("json_exposure", []):
        add("JSON_EXPOSURE", f"Key: {exp['key']}", "primary:body", "HIGH", [exp])
    for istate in body.get("inline_data", []):
        add("CLIENT_STATE_LEAK", "Inline state object in HTML",
            "primary:body:inline", "MEDIUM", [istate[:100]])

    # TLS
    for port, tdata in p.get("tls", {}).items():
        if tdata.get("expired"):
            add("TLS_EXPIRED", f"Port {port} cert expired",
                f"primary:tls:{port}", "HIGH", [tdata])
        if tdata.get("self_signed"):
            add("TLS_SELF_SIGNED", f"Port {port} self-signed cert",
                f"primary:tls:{port}", "MEDIUM", [tdata])
        if tdata.get("bits", 256) < 128:
            add("WEAK_CIPHER", f"Port {port}: {tdata.get('cipher')}",
                f"primary:tls:{port}", "HIGH", [tdata])
        for san in tdata.get("sans", []):
            if any(k in san.lower() for k in ["internal","dev","staging","vpn","admin","corp"]):
                add("INTERESTING_SAN", san, f"primary:tls:{port}", "MEDIUM", [san])

    # Proxy
    proxy = p.get("proxy", {})
    if proxy.get("proxy_detected"):
        add("PROXY_DETECTED", proxy.get("proxy_type","unknown"),
            "primary:proxy", "HIGH", proxy.get("signals",[]))

    # Crawl findings
    for item in p.get("crawl", {}).get("findings", []):
        for f in item.get("findings", []):
            ftype = f.get("type","").upper()
            add(ftype, str(f.get("data",""))[:120],
                f"crawl:{item['url']}", "MEDIUM", [f])

    # Robots disallowed paths
    for path in p.get("robots", {}).get("disallowed", []):
        conf = "HIGH" if any(k in path.lower() for k in
               ["admin","backup","config","debug","secret","private"]) else "LOW"
        add("ROBOTS_DISALLOW", path, "primary:robots", conf)

    # Open ports
    port_counter = {}
    for op in p.get("ports", []):
        port_counter[op["port"]] = port_counter.get(op["port"], 0) + 1
        svc = op.get("service","unknown")
        ver = op.get("version","")
        conf = "HIGH" if op["port"] in (21,23,445,1433,3306,5432,6379,
                                         27017,2375,4848,7001,8888,9200) else "LOW"
        add("OPEN_PORT", f"{op['port']}/{svc} {ver[:40]}",
            f"primary:port:{op['port']}", conf, [op])

    # ── Pull from subdomains ─────────────────────────────────────
    sub_port_counter = {}
    for sub_host, sdata in master.get("subdomains", {}).items():
        # Headers
        shdr = sdata.get("headers", {})
        for item in shdr.get("dangerous", []):
            add("DANGEROUS_HEADER", f"{sub_host}: {item['note']}",
                f"sub:{sub_host}:{item['header']}", "HIGH", [item])

        # Body errors
        sbody = sdata.get("body", {})
        for err in sbody.get("errors", []):
            add("ERROR_LEAK", f"{sub_host}: {err['type']}",
                f"sub:{sub_host}:body", "HIGH", err["samples"])
        for exp in sbody.get("json_exposure", []):
            add("JSON_EXPOSURE", f"{sub_host} key:{exp['key']}",
                f"sub:{sub_host}:body", "HIGH", [exp])

        # TLS on subdomains
        for port, tdata in sdata.get("tls", {}).items():
            if tdata.get("self_signed"):
                add("TLS_SELF_SIGNED", f"{sub_host}:{port}",
                    f"sub:{sub_host}:tls", "MEDIUM", [tdata])

        # Port tracking for pattern detection
        for op in sdata.get("ports", []):
            p_key = op["port"]
            sub_port_counter[p_key] = sub_port_counter.get(p_key, 0) + 1

    # Pattern: same port open across 3+ hosts = shared infra / misconfigured firewall
    for port_num, count in sub_port_counter.items():
        if count >= 3:
            add("SHARED_PORT_PATTERN",
                f"Port {port_num} open on {count} subdomains — shared infra or wide firewall gap",
                "correlation:port_pattern", "HIGH",
                [{"port": port_num, "count": count}])

    # ── Cross-signal rules ───────────────────────────────────────
    types_seen = {f["type"] for f in findings}

    # Debug header + error leak = dev environment exposed to internet
    if "DANGEROUS_HEADER" in types_seen and "ERROR_LEAK" in types_seen:
        add("COMPOSITE", "Debug headers + error leaks — likely dev/staging exposed",
            "correlation:composite", "HIGH",
            ["DANGEROUS_HEADER", "ERROR_LEAK"])

    # Self-signed cert + admin port open = internal tool exposed
    admin_ports = {4848, 7001, 8888, 9200, 5601, 8161, 15672}
    open_port_nums = {op["port"] for op in p.get("ports", [])}
    if "TLS_SELF_SIGNED" in types_seen and open_port_nums & admin_ports:
        add("COMPOSITE",
            f"Self-signed cert + admin port(s) open: {open_port_nums & admin_ports}",
            "correlation:composite", "HIGH",
            list(open_port_nums & admin_ports))

    # Missing HSTS + proxy detected = potential HTTPS downgrade path
    missing_hdrs = {f["detail"] for f in findings if f["type"] == "MISSING_SEC_HEADER"}
    if "HSTS missing — HTTPS downgrade possible" in missing_hdrs and \
       "PROXY_DETECTED" in types_seen:
        add("COMPOSITE", "Missing HSTS + proxy in path — HTTPS stripping risk",
            "correlation:composite", "MEDIUM",
            ["MISSING_SEC_HEADER:HSTS", "PROXY_DETECTED"])

    # ── Confidence upgrade pass ──────────────────────────────────
    # Group by type — if same finding type appears from 2+ sources → upgrade
    from collections import Counter
    type_counts = Counter(f["type"] for f in findings)
    for f in findings:
        n = type_counts[f["type"]]
        if n >= 3 and f["confidence"] == "LOW":
            f["confidence"] = "MEDIUM"
        elif n >= 5 and f["confidence"] == "MEDIUM":
            f["confidence"] = "HIGH"

    # Sort: HIGH first, then MEDIUM, then LOW
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda x: order.get(x["confidence"], 3))
    return findings


# ═══════════════════════════════════════════════════════════════
#  MODULE 17 — HTML REPORT GENERATOR
#
#  master dict → single self-contained HTML file.
#  No external deps — CSS inline, works offline.
#  Layout:
#    - Header: target, timestamp, score badge
#    - Priority findings: HIGH/MEDIUM/LOW sections
#    - Subdomain map table
#    - Open ports table
#    - Raw JSON collapse panel
# ═══════════════════════════════════════════════════════════════

def generate_html_report(master: dict, out_path: str = None) -> str:
    target    = master.get("target", "unknown")
    ts        = master.get("timestamp", datetime.now().isoformat())
    findings  = master.get("all_findings", [])
    primary   = master.get("primary", {})
    subdoms   = master.get("subdomains", {})
    ip        = primary.get("ip", "")

    high   = [f for f in findings if f["confidence"] == "HIGH"]
    medium = [f for f in findings if f["confidence"] == "MEDIUM"]
    low    = [f for f in findings if f["confidence"] == "LOW"]

    open_ports = primary.get("ports", [])
    geo        = primary.get("geo", {})
    proxy      = primary.get("proxy", {})

    def badge(conf):
        colors = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#7f8c8d"}
        return (f'<span style="background:{colors.get(conf,"#555")};color:#fff;'
                f'padding:2px 8px;border-radius:3px;font-size:11px;'
                f'font-weight:bold">{conf}</span>')

    def finding_rows(flist):
        if not flist:
            return '<tr><td colspan="3" style="color:#666;padding:12px">None</td></tr>'
        rows = ""
        for f in flist:
            ev = ""
            if f.get("evidence"):
                ev = (f'<details><summary style="cursor:pointer;color:#aaa;font-size:11px">'
                      f'evidence</summary><pre style="font-size:10px;color:#ccc;'
                      f'white-space:pre-wrap">{json.dumps(f["evidence"],indent=2,default=str)[:400]}'
                      f'</pre></details>')
            rows += (f'<tr>'
                     f'<td style="padding:8px 12px;color:#e0e0e0;font-family:monospace">'
                     f'{f["type"]}</td>'
                     f'<td style="padding:8px 12px;color:#ccc">{f["detail"]}</td>'
                     f'<td style="padding:8px 12px">{badge(f["confidence"])}{ev}</td>'
                     f'</tr>')
        return rows

    def port_rows():
        if not open_ports:
            return '<tr><td colspan="4" style="color:#666;padding:12px">No open ports</td></tr>'
        rows = ""
        for p in open_ports:
            tls_b = ('<span style="color:#2ecc71">✓ TLS</span>'
                     if p.get("tls") else
                     '<span style="color:#555">—</span>')
            rows += (f'<tr>'
                     f'<td style="padding:6px 12px;color:#2ecc71;font-weight:bold">'
                     f'{p["port"]}</td>'
                     f'<td style="padding:6px 12px;color:#e0e0e0">{p.get("service","?")}</td>'
                     f'<td style="padding:6px 12px;color:#aaa;font-size:12px">'
                     f'{p.get("version","")[:60]}</td>'
                     f'<td style="padding:6px 12px">{tls_b}</td>'
                     f'</tr>')
        return rows

    def sub_rows():
        if not subdoms:
            return '<tr><td colspan="4" style="color:#666;padding:12px">None discovered</td></tr>'
        rows = ""
        for sh, sd in subdoms.items():
            n_open = len(sd.get("ports", []))
            n_err  = len(sd.get("body", {}).get("errors", []))
            flag   = "🔴" if n_err else ("🟡" if n_open > 3 else "🟢")
            rows += (f'<tr>'
                     f'<td style="padding:6px 12px;color:#3498db;font-family:monospace">'
                     f'{sh}</td>'
                     f'<td style="padding:6px 12px;color:#aaa">{sd.get("ip","?")}</td>'
                     f'<td style="padding:6px 12px;color:#2ecc71">{n_open} open</td>'
                     f'<td style="padding:6px 12px;font-size:16px">{flag}</td>'
                     f'</tr>')
        return rows

    risk_score = len(high) * 10 + len(medium) * 3 + len(low)
    risk_label = ("CRITICAL" if risk_score >= 50 else
                  "HIGH"     if risk_score >= 25 else
                  "MEDIUM"   if risk_score >= 10 else "LOW")
    risk_color = {"CRITICAL":"#e74c3c","HIGH":"#e67e22",
                  "MEDIUM":"#f39c12","LOW":"#27ae60"}[risk_label]

    frameworks = [fw["name"] for fw in primary.get("body",{}).get("frameworks",[])]
    stack_str  = ", ".join(frameworks) if frameworks else "Unknown"
    proxy_str  = proxy.get("proxy_type","None detected") if proxy.get("proxy_detected") else "None detected"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ReconX Report — {target}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0d1117;color:#e0e0e0;font-family:'Segoe UI',system-ui,sans-serif;
        font-size:14px;line-height:1.6}}
  .wrap{{max-width:1100px;margin:0 auto;padding:32px 20px}}
  h1{{font-size:26px;font-weight:700;color:#fff;margin-bottom:4px}}
  h2{{font-size:15px;font-weight:600;color:#aaa;margin:28px 0 10px;
      text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #222;
      padding-bottom:6px}}
  .meta{{color:#666;font-size:12px;margin-bottom:28px}}
  .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;
           margin-bottom:28px}}
  .card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:16px}}
  .card .val{{font-size:28px;font-weight:700;margin-bottom:2px}}
  .card .lbl{{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px}}
  .risk-badge{{display:inline-block;background:{risk_color};color:#fff;
               font-size:13px;font-weight:700;padding:4px 16px;border-radius:20px;
               margin-bottom:20px}}
  table{{width:100%;border-collapse:collapse;background:#161b22;
         border:1px solid #21262d;border-radius:8px;overflow:hidden}}
  th{{padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;
      letter-spacing:1px;color:#666;border-bottom:1px solid #21262d;
      background:#0d1117}}
  tr:hover td{{background:#1c2128}}
  .section{{margin-bottom:32px}}
  details summary{{outline:none}}
  pre{{background:#0d1117;padding:12px;border-radius:6px;overflow-x:auto;
       font-size:12px;color:#aaa;margin-top:8px;border:1px solid #21262d}}
  .pill{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;
          font-weight:600;margin:2px}}
  .info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:24px}}
  .info-item{{background:#161b22;border:1px solid #21262d;border-radius:6px;
               padding:12px 16px}}
  .info-item .k{{font-size:11px;color:#555;text-transform:uppercase;letter-spacing:1px}}
  .info-item .v{{color:#e0e0e0;font-family:monospace;margin-top:2px;word-break:break-all}}
</style>
</head>
<body>
<div class="wrap">

  <h1>ReconX Report</h1>
  <div class="meta">Target: <b style="color:#58a6ff">{target}</b> &nbsp;|&nbsp;
    IP: <b>{ip}</b> &nbsp;|&nbsp; {ts}</div>

  <div class="risk-badge">RISK: {risk_label} (score: {risk_score})</div>

  <div class="cards">
    <div class="card">
      <div class="val" style="color:#e74c3c">{len(high)}</div>
      <div class="lbl">High Findings</div>
    </div>
    <div class="card">
      <div class="val" style="color:#f39c12">{len(medium)}</div>
      <div class="lbl">Medium Findings</div>
    </div>
    <div class="card">
      <div class="val" style="color:#7f8c8d">{len(low)}</div>
      <div class="lbl">Low Findings</div>
    </div>
    <div class="card">
      <div class="val" style="color:#3498db">{len(open_ports)}</div>
      <div class="lbl">Open Ports</div>
    </div>
    <div class="card">
      <div class="val" style="color:#9b59b6">{len(subdoms)}</div>
      <div class="lbl">Subdomains</div>
    </div>
  </div>

  <div class="info-grid">
    <div class="info-item">
      <div class="k">Location</div>
      <div class="v">{geo.get('city','?')}, {geo.get('country','?')}</div>
    </div>
    <div class="info-item">
      <div class="k">ASN / Org</div>
      <div class="v">{geo.get('org','?')}</div>
    </div>
    <div class="info-item">
      <div class="k">Detected Stack</div>
      <div class="v">{stack_str}</div>
    </div>
    <div class="info-item">
      <div class="k">Proxy / CDN</div>
      <div class="v">{proxy_str}</div>
    </div>
  </div>

  <div class="section">
    <h2>🔴 High Confidence Findings</h2>
    <table>
      <tr><th>Type</th><th>Detail</th><th>Confidence</th></tr>
      {finding_rows(high)}
    </table>
  </div>

  <div class="section">
    <h2>🟡 Medium Confidence Findings</h2>
    <table>
      <tr><th>Type</th><th>Detail</th><th>Confidence</th></tr>
      {finding_rows(medium)}
    </table>
  </div>

  <div class="section">
    <h2>⚪ Low Confidence Findings</h2>
    <table>
      <tr><th>Type</th><th>Detail</th><th>Confidence</th></tr>
      {finding_rows(low)}
    </table>
  </div>

  <div class="section">
    <h2>Open Ports</h2>
    <table>
      <tr><th>Port</th><th>Service</th><th>Version</th><th>TLS</th></tr>
      {port_rows()}
    </table>
  </div>

  <div class="section">
    <h2>Subdomains</h2>
    <table>
      <tr><th>Host</th><th>IP</th><th>Ports</th><th>Status</th></tr>
      {sub_rows()}
    </table>
  </div>

  <div class="section">
    <h2>Raw Data</h2>
    <details>
      <summary style="cursor:pointer;color:#58a6ff;padding:8px 0">
        Click to expand raw JSON
      </summary>
      <pre>{json.dumps({k:v for k,v in master.items()
                        if k not in ('all_findings',)},
                       indent=2, default=str)[:8000]}
... (truncated — see saved JSON for full data)</pre>
    </details>
  </div>

  <div style="margin-top:40px;padding-top:16px;border-top:1px solid #21262d;
              color:#444;font-size:11px;text-align:center">
    ReconX v3 &nbsp;·&nbsp; Generated {ts} &nbsp;·&nbsp;
    Authorized testing only
  </div>
</div>
</body>
</html>"""

    if out_path is None:
        Path("recon_output").mkdir(exist_ok=True)
        out_path = f"recon_output/report_{target.replace('.','_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    log("REPORT", f"HTML report → {out_path}", C['M'])
    return out_path

# ═══════════════════════════════════════════════════════════════
#  MODULE 18 — SAVE
# ═══════════════════════════════════════════════════════════════
def save(data: dict, filename: str):
    Path("recon_output").mkdir(exist_ok=True)
    path = f"recon_output/{filename}"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    log("SAVED", f"→ {path}", C['M'])

# ═══════════════════════════════════════════════════════════════
#  MAIN MENU
# ═══════════════════════════════════════════════════════════════
def get_jitter() -> JitterEngine:
    print(f"\n  {C['W']}Scan mode:{C['RST']}")
    print(f"  {C['G']}1{C['RST']}.  Fast   — Max throughput, more visible")
    print(f"  {C['Y']}2{C['RST']}.  Normal — Balanced (default)")
    print(f"  {C['R']}3{C['RST']}.  Silent — Low-and-slow, IDS evasion")
    choice = input(f"  {C['C']}Mode (1/2/3):{C['RST']} ").strip()
    modes = {"1": "fast", "2": "normal", "3": "silent"}
    mode = modes.get(choice, "normal")
    log("MODE", mode.upper(), C['Y'])
    return JitterEngine(mode)

def parse_ports(pr: str) -> list:
    """
    Accepts:
      ""           → 1-1024 default
      "all"        → 1-65535
      "common"     → curated 150 common ports
      "80,443,8080"→ comma list
      "1-1024"     → range
      "80,443,8000-9000,27017" → mixed
    Clamps every port to 1-65535. Dedupes. Sorted.
    """
    COMMON_PORTS = [
        21,22,23,25,53,80,110,111,135,139,143,443,445,465,
        587,993,995,1080,1433,1521,1723,2049,2375,2376,3306,
        3389,3690,4444,4848,5432,5900,5984,6379,7001,7002,
        7070,7443,8000,8080,8081,8088,8443,8444,8888,8983,
        9000,9090,9200,9300,9418,9999,10000,11211,27017,
        27018,28017,50000,50070,50075,61616,902,912,5044,
        5601,9600,4200,3000,3001,4000,4001,5000,5001,6000,
        6001,7000,8008,8009,8010,8020,8030,8086,8090,8091,
        8161,8500,8787,9001,9002,9003,9005,9010,9042,9060,
        9080,9081,9100,9160,9292,9390,9443,9502,9503,9600,
        9700,9800,9900,9981,10001,10050,10051,10080,10443,
        11000,11300,12017,12345,13000,13306,14000,15672,
        16010,16000,17000,18080,18443,20000,22022,25000,
        27015,28015,32400,49152,
    ]

    pr = pr.strip().lower()
    if not pr:
        return list(range(1, 1025))
    if pr == "all":
        log("INFO", "Full sweep: ports 1–65535 (~65k ports)", C['Y'])
        return list(range(1, 65536))
    if pr == "common":
        log("INFO", f"Common preset: {len(COMMON_PORTS)} curated ports", C['Y'])
        return sorted(COMMON_PORTS)

    ports = set()
    for token in pr.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            parts = token.split("-", 1)
            try:
                lo = max(1,     int(parts[0].strip()))
                hi = min(65535, int(parts[1].strip()))
                if lo > hi:
                    lo, hi = hi, lo
                ports.update(range(lo, hi + 1))
            except ValueError:
                log("WARN", f"Bad range token ignored: '{token}'", C['Y'])
        elif token.isdigit():
            p = int(token)
            if 1 <= p <= 65535:
                ports.add(p)
            else:
                log("WARN", f"Port out of range ignored: {p}", C['Y'])
        else:
            log("WARN", f"Unknown token ignored: '{token}'", C['Y'])

    if not ports:
        log("WARN", "No valid ports parsed — falling back to 1-1024", C['Y'])
        return list(range(1, 1025))

    result = sorted(ports)
    log("INFO", f"Ports queued: {len(result)}  range: {result[0]}–{result[-1]}", C['C'])
    return result

def menu():
    banner()
    print(f"  {C['R']}0.{C['RST']}  ★ AUTO RECON    (full chain + HTML report — recommended)")
    print(f"  {C['DIM']}{'─'*48}{C['RST']}")
    print(f"  {C['W']}1.{C['RST']}  Full Recon    (DNS + WHOIS + Geo + Crawl + Scan)")
    print(f"  {C['W']}2.{C['RST']}  Port Scan     (with fingerprinting)")
    print(f"  {C['W']}3.{C['RST']}  Web Crawl     (Endpoints + Hidden Content)")
    print(f"  {C['W']}4.{C['RST']}  Crawl + Scan")
    print(f"  {C['W']}5.{C['RST']}  Scan from File (batch from crawl JSON)")
    print(f"  {C['W']}6.{C['RST']}  WHOIS Lookup")
    print(f"  {C['W']}7.{C['RST']}  DNS Lookup")
    print(f"  {C['W']}8.{C['RST']}  IP Geolocation")
    print(f"  {C['W']}9.{C['RST']}  TLS Cert Enum        (SANs + cipher + expiry)")
    print(f"  {C['W']}10.{C['RST']} Robots + Sitemap     Harvest")
    print(f"  {C['W']}11.{C['RST']} CT Subdomain Enum    (crt.sh, zero bruteforce)")
    print(f"  {C['W']}12.{C['RST']} Dork Generator       (Google + Bing queries)")
    print(f"  {C['W']}13.{C['RST']} Header Intelligence  (stack + misconfig + probe)")
    print(f"  {C['W']}14.{C['RST']} Reverse Proxy Detect (timing + signal analysis)")
    print(f"  {C['W']}15.{C['RST']} Deep Response Analyze(body: HTML/JSON/React/errors)")
    print()
    return input(f"  {C['C']}Choice:{C['RST']} ").strip()

if __name__ == "__main__":
    choice  = menu()
    jitter  = get_jitter()

    if choice == "0":
        target = input(f"  {C['C']}Target (domain or IP):{C['RST']} ").strip()
        pr     = input(f"  {C['C']}Ports [enter=common | all | 80,443 | 1-9999]:{C['RST']} ").strip() or "common"
        master = auto_correlate(target, jitter, ports_input=pr)
        html_path = generate_html_report(master)
        log("INFO", f"Auto-recon complete", C['G'])
        log("INFO", f"HTML report: {html_path}", C['M'])
        if input(f"\n  {C['C']}Save raw JSON too? (y/n):{C['RST']} ").lower() == "y":
            fname = input(f"  {C['C']}Filename:{C['RST']} ").strip() or f"auto_{target.replace('.','_')}.json"
            save(master, fname)

    elif choice == "1":
        target = input(f"  {C['C']}Target:{C['RST']} ").strip()
        host, ip = resolve(target)
        if not ip: exit()
        pr     = input(f"  {C['C']}Ports [enter=1-1024 | all | common | 80,443 | 1-9999]:{C['RST']} ").strip()
        ports  = parse_ports(pr)
        report = {"target": target, "ip": ip}
        report["whois"]    = whois_lookup(host)
        report["dns"]      = dns_lookup(host)
        report["geo"]      = geoip(ip)
        report["tls"]      = tls_enum(host)
        report["robots"]   = harvest_robots_sitemap(f"http://{host}")
        report["subdomains"]= ct_subdomain_enum(host)
        report["headers"]  = header_intelligence(f"http://{host}")
        report["proxy"]    = reverse_proxy_detect(host, ip)
        report["body"]     = deep_response_analyze(f"http://{host}")
        report["crawl"]    = crawl(f"http://{host}", jitter=jitter)
        op, fl             = run_scan(ip, ports, host, jitter)
        report["ports"]    = op
        report["filtered"] = fl
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(report, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "full_recon.json")

    elif choice == "2":
        target = input(f"  {C['C']}Target:{C['RST']} ").strip()
        host, ip = resolve(target)
        if not ip: exit()
        pr     = input(f"  {C['C']}Ports [enter=1-1024 | all | common | 80,443 | 1-9999]:{C['RST']} ").strip()
        ports  = parse_ports(pr)
        op, fl = run_scan(ip, ports, host, jitter)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save({"open": op, "filtered": fl},
                 input(f"  {C['C']}Filename:{C['RST']} ").strip() or "scan.json")

    elif choice == "3":
        target = input(f"  {C['C']}Target URL:{C['RST']} ").strip()
        depth  = input(f"  {C['C']}Depth (enter=2):{C['RST']} ").strip()
        result = crawl(target, int(depth) if depth else 2, jitter)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "crawl.json")

    elif choice == "4":
        target = input(f"  {C['C']}Target URL:{C['RST']} ").strip()
        depth  = input(f"  {C['C']}Depth:{C['RST']} ").strip()
        pr     = input(f"  {C['C']}Ports:{C['RST']} ").strip()
        ports  = parse_ports(pr)
        host, ip = resolve(target)
        if not ip: exit()
        crawl_result = crawl(target, int(depth) if depth else 2, jitter)
        op, fl = run_scan(ip, ports, host, jitter)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save({"crawl": crawl_result, "ports": op},
                 input(f"  {C['C']}Filename:{C['RST']} ").strip() or "crawl_scan.json")

    elif choice == "5":
        fname = input(f"  {C['C']}Crawl JSON file:{C['RST']} ").strip()
        pr    = input(f"  {C['C']}Ports:{C['RST']} ").strip()
        ports = parse_ports(pr)
        with open(fname) as f:
            data = json.load(f)
        urls = data.get("urls", [])
        section(f"BATCH SCAN — {len(urls)} URLs")
        results = {}
        for url in urls:
            h = urlparse(url).hostname
            if not h: continue
            _, ip = resolve(h)
            if ip:
                op, _ = run_scan(ip, ports, h, jitter)
                results[url] = op
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(results, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "batch.json")

    elif choice == "6":
        domain = input(f"  {C['C']}Domain:{C['RST']} ").strip()
        result = whois_lookup(domain)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, "whois.json")

    elif choice == "7":
        domain = input(f"  {C['C']}Domain:{C['RST']} ").strip()
        result = dns_lookup(domain)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, "dns.json")

    elif choice == "8":
        ip     = input(f"  {C['C']}IP Address:{C['RST']} ").strip()
        result = geoip(ip)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, "geo.json")

    elif choice == "9":
        target = input(f"  {C['C']}Host (domain or IP):{C['RST']} ").strip()
        pr     = input(f"  {C['C']}Ports (enter=default 443,8443,993...):{C['RST']} ").strip()
        ports  = [int(p.strip()) for p in pr.split(",") if p.strip().isdigit()] or None
        result = tls_enum(target, ports)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "tls.json")

    elif choice == "10":
        target = input(f"  {C['C']}Base URL (e.g. http://example.com):{C['RST']} ").strip()
        result = harvest_robots_sitemap(target)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "robots_sitemap.json")

    elif choice == "11":
        domain = input(f"  {C['C']}Domain:{C['RST']} ").strip()
        result = ct_subdomain_enum(domain)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "subdomains.json")

    elif choice == "12":
        domain   = input(f"  {C['C']}Domain:{C['RST']} ").strip()
        auto     = input(f"  {C['C']}Auto-open top 5 in browser? (y/n):{C['RST']} ").lower() == "y"
        result   = dork_generator(domain, auto_open=auto)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "dorks.json")

    elif choice == "13":
        target = input(f"  {C['C']}URL (e.g. https://example.com):{C['RST']} ").strip()
        result = header_intelligence(target)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "headers.json")

    elif choice == "14":
        target   = input(f"  {C['C']}Host:{C['RST']} ").strip()
        host, ip = resolve(target)
        if not ip: exit()
        result   = reverse_proxy_detect(host, ip)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "proxy.json")

    elif choice == "15":
        target = input(f"  {C['C']}URL (e.g. https://example.com):{C['RST']} ").strip()
        result = deep_response_analyze(target)
        if input(f"\n  {C['C']}Save? (y/n):{C['RST']} ").lower() == "y":
            save(result, input(f"  {C['C']}Filename:{C['RST']} ").strip() or "body_analysis.json")
