#!/usr/bin/env python3
"""
ReconX GUI — Desktop Interface
Run: python3 reconx_gui.py
Requires: reconx_v3.py same directory
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import json
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# ── Engine import ────────────────────────────────────────────────
try:
    import reconx_v3 as engine
except ImportError:
    print("ERROR: reconx_v3.py not found in same directory")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
#  THEME — Dark terminal aesthetic
# ═══════════════════════════════════════════════════════════════
THEME = {
    "bg":        "#0d1117",
    "bg2":       "#161b22",
    "bg3":       "#21262d",
    "fg":        "#e6edf3",
    "fg_dim":    "#7d8590",
    "green":     "#3fb950",
    "red":       "#f85149",
    "yellow":    "#d29922",
    "blue":      "#58a6ff",
    "purple":    "#bc8cff",
    "cyan":      "#39d353",
    "orange":    "#f0883e",
    "border":    "#30363d",
    "select":    "#1f6feb",
    "font_mono": ("JetBrains Mono", 11) if sys.platform != "win32"
                 else ("Consolas", 11),
    "font_ui":   ("Segoe UI", 11) if sys.platform == "win32"
                 else ("Ubuntu", 11),
    "font_head": ("Segoe UI", 13, "bold") if sys.platform == "win32"
                 else ("Ubuntu", 13, "bold"),
}

# ═══════════════════════════════════════════════════════════════
#  LOG QUEUE — thread-safe output from engine → GUI
# ═══════════════════════════════════════════════════════════════
log_queue    = queue.Queue()
result_queue = queue.Queue()

# Tag colours for terminal output widget
LOG_TAG_COLORS = {
    "OPEN":       THEME["green"],
    "FOUND":      THEME["yellow"],
    "DANGER":     THEME["red"],
    "MISSING":    THEME["yellow"],
    "STACK":      THEME["cyan"],
    "SIGNAL":     THEME["orange"],
    "HIGH":       THEME["red"],
    "MEDIUM":     THEME["yellow"],
    "LOW":        THEME["fg_dim"],
    "DONE":       THEME["green"],
    "INFO":       THEME["blue"],
    "ERR":        THEME["red"],
    "WARN":       THEME["yellow"],
    "CHAIN":      THEME["purple"],
    "CONFIRMED":  THEME["green"],
    "DNS":        THEME["blue"],
    "CHUNK":      THEME["fg_dim"],
    "SAVED":      THEME["purple"],
    "REPORT":     THEME["purple"],
    "CRAWL":      THEME["blue"],
    "API":        THEME["yellow"],
    "CT":         THEME["cyan"],
    "DORK":       THEME["orange"],
    "PROBE":      THEME["purple"],
    "RESULT":     THEME["green"],
    "SCORE":      THEME["orange"],
    "FRAMEWORK":  THEME["cyan"],
    "META":       THEME["fg_dim"],
    "FORM":       THEME["blue"],
    "ERROR_LEAK": THEME["red"],
    "JSON_EXPOSE":THEME["red"],
    "COMMENT":    THEME["yellow"],
    "SSL":        THEME["yellow"],
    "PORT":       THEME["blue"],
    "CN":         THEME["fg"],
    "ISSUER":     THEME["fg_dim"],
    "EXPIRY":     THEME["green"],
    "SANs":       THEME["yellow"],
}

def gui_log(tag: str, msg: str, color: str = None):
    """Drop-in replacement for engine.log() — routes to queue."""
    color = color or THEME["fg"]
    ts    = datetime.now().strftime("%H:%M:%S")
    log_queue.put(("log", ts, tag, msg, color))

def gui_section(title: str):
    log_queue.put(("section", title))

# Monkey-patch engine output functions
engine.log     = gui_log
engine.section = gui_section

# ═══════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════
class ReconXApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ReconX v3  —  Recon & Intelligence Suite")
        self.geometry("1280x820")
        self.minsize(900, 600)
        self.configure(bg=THEME["bg"])

        # State
        self._running    = False
        self._thread     = None
        self._master_data = {}

        self._setup_style()
        self._build_menu()
        self._build_layout()
        self._poll_queues()

    # ── ttk Style ───────────────────────────────────────────────
    def _setup_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure(".",
            background=THEME["bg"], foreground=THEME["fg"],
            fieldbackground=THEME["bg2"], bordercolor=THEME["border"],
            darkcolor=THEME["bg2"], lightcolor=THEME["bg3"],
            troughcolor=THEME["bg3"], insertcolor=THEME["fg"],
            selectbackground=THEME["select"], selectforeground="#fff")

        s.configure("TFrame",   background=THEME["bg"])
        s.configure("TLabel",   background=THEME["bg"],  foreground=THEME["fg"])
        s.configure("TButton",
            background=THEME["bg3"], foreground=THEME["fg"],
            relief="flat", padding=(10, 6), borderwidth=0)
        s.map("TButton",
            background=[("active", THEME["select"]),
                        ("disabled", THEME["bg2"])],
            foreground=[("disabled", THEME["fg_dim"])])

        s.configure("Accent.TButton",
            background=THEME["select"], foreground="#fff",
            relief="flat", padding=(12, 8))
        s.map("Accent.TButton",
            background=[("active", "#1a7fe8")])

        s.configure("Danger.TButton",
            background="#b91c1c", foreground="#fff",
            relief="flat", padding=(10, 6))
        s.map("Danger.TButton",
            background=[("active", "#dc2626")])

        s.configure("TEntry",
            fieldbackground=THEME["bg2"], foreground=THEME["fg"],
            insertcolor=THEME["fg"], relief="flat",
            borderwidth=1, padding=6)

        s.configure("TCombobox",
            fieldbackground=THEME["bg2"], foreground=THEME["fg"],
            selectbackground=THEME["select"])

        s.configure("TNotebook",
            background=THEME["bg"], bordercolor=THEME["border"])
        s.configure("TNotebook.Tab",
            background=THEME["bg3"], foreground=THEME["fg_dim"],
            padding=(14, 6))
        s.map("TNotebook.Tab",
            background=[("selected", THEME["bg2"])],
            foreground=[("selected", THEME["blue"])])

        s.configure("Treeview",
            background=THEME["bg2"], foreground=THEME["fg"],
            fieldbackground=THEME["bg2"], rowheight=24,
            borderwidth=0)
        s.configure("Treeview.Heading",
            background=THEME["bg3"], foreground=THEME["fg_dim"],
            relief="flat", padding=(8, 6))
        s.map("Treeview",
            background=[("selected", THEME["select"])],
            foreground=[("selected", "#fff")])

        s.configure("Horizontal.TProgressbar",
            background=THEME["blue"], troughcolor=THEME["bg3"],
            borderwidth=0, thickness=4)

        s.configure("TSeparator", background=THEME["border"])

    # ── Menu bar ────────────────────────────────────────────────
    def _build_menu(self):
        mb = tk.Menu(self, bg=THEME["bg2"], fg=THEME["fg"],
                     activebackground=THEME["select"],
                     activeforeground="#fff", relief="flat",
                     borderwidth=0)
        self.config(menu=mb)

        # File
        fm = tk.Menu(mb, tearoff=0, bg=THEME["bg2"], fg=THEME["fg"],
                     activebackground=THEME["select"],
                     activeforeground="#fff")
        fm.add_command(label="Save JSON",        command=self._save_json)
        fm.add_command(label="Save HTML Report", command=self._save_html)
        fm.add_separator()
        fm.add_command(label="Clear Terminal",   command=self._clear_terminal)
        fm.add_separator()
        fm.add_command(label="Exit",             command=self.destroy)
        mb.add_cascade(label="File", menu=fm)

        # Help
        hm = tk.Menu(mb, tearoff=0, bg=THEME["bg2"], fg=THEME["fg"],
                     activebackground=THEME["select"],
                     activeforeground="#fff")
        hm.add_command(label="About ReconX", command=self._show_about)
        mb.add_cascade(label="Help", menu=hm)

    # ── Main layout ──────────────────────────────────────────────
    def _build_layout(self):
        # ─── TOP: header bar ────────────────────────────────────
        hdr = tk.Frame(self, bg=THEME["bg2"], height=52)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="  ◈ ReconX",
                 bg=THEME["bg2"], fg=THEME["blue"],
                 font=(THEME["font_head"][0], 16, "bold")).pack(side="left", padx=8)
        tk.Label(hdr, text="v3 — Recon & Intelligence Suite",
                 bg=THEME["bg2"], fg=THEME["fg_dim"],
                 font=THEME["font_ui"]).pack(side="left")

        tk.Label(hdr, text="by Faizan  ·  github.com/faizu526",
                 bg=THEME["bg2"], fg=THEME["fg_dim"],
                 font=(THEME["font_mono"][0], 9)).pack(side="left", padx=20)

        self._status_var = tk.StringVar(value="Ready")
        tk.Label(hdr, textvariable=self._status_var,
                 bg=THEME["bg2"], fg=THEME["green"],
                 font=THEME["font_mono"]).pack(side="right", padx=16)

        # ─── MAIN: paned window ─────────────────────────────────
        paned = tk.PanedWindow(self, orient="horizontal",
                               bg=THEME["border"], sashwidth=4,
                               sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=0, pady=0)

        # Left panel
        left = self._build_left_panel()
        paned.add(left, minsize=280, width=300)

        # Right panel
        right = self._build_right_panel()
        paned.add(right, minsize=500)

        # ─── BOTTOM: progress + status ──────────────────────────
        bot = tk.Frame(self, bg=THEME["bg2"], height=32)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)

        self._prog = ttk.Progressbar(bot, mode="indeterminate",
                                     style="Horizontal.TProgressbar")
        self._prog.pack(fill="x", padx=0, pady=0, side="top")

        self._bot_label = tk.Label(bot,
                                   text="  Authorized testing only  ·  Built by Faizan · github.com/faizu526",
                                   bg=THEME["bg2"], fg=THEME["fg_dim"],
                                   font=(THEME["font_mono"][0], 9))
        self._bot_label.pack(side="left")

    # ── Left panel — controls ────────────────────────────────────
    def _build_left_panel(self):
        frame = tk.Frame(self, bg=THEME["bg"], width=300)
        frame.pack_propagate(False)

        # Target input
        inp_frame = tk.Frame(frame, bg=THEME["bg"])
        inp_frame.pack(fill="x", padx=12, pady=(14, 6))

        tk.Label(inp_frame, text="TARGET", bg=THEME["bg"],
                 fg=THEME["fg_dim"],
                 font=(THEME["font_mono"][0], 9)).pack(anchor="w")
        self._target_var = tk.StringVar()
        e = ttk.Entry(inp_frame, textvariable=self._target_var,
                      font=THEME["font_mono"])
        e.pack(fill="x", pady=(2, 0))
        e.bind("<Return>", lambda _: self._run_module())

        # Ports input
        tk.Label(inp_frame, text="PORTS", bg=THEME["bg"],
                 fg=THEME["fg_dim"],
                 font=(THEME["font_mono"][0], 9)).pack(anchor="w", pady=(8, 0))
        self._ports_var = tk.StringVar(value="common")
        ttk.Entry(inp_frame, textvariable=self._ports_var,
                  font=THEME["font_mono"]).pack(fill="x", pady=(2, 0))

        tk.Label(inp_frame,
                 text="common | all | 80,443 | 1-9999",
                 bg=THEME["bg"], fg=THEME["fg_dim"],
                 font=(THEME["font_mono"][0], 8)).pack(anchor="w")

        # Jitter mode
        tk.Label(inp_frame, text="SCAN MODE", bg=THEME["bg"],
                 fg=THEME["fg_dim"],
                 font=(THEME["font_mono"][0], 9)).pack(anchor="w", pady=(8, 0))
        self._mode_var = tk.StringVar(value="normal")
        mode_box = ttk.Combobox(inp_frame, textvariable=self._mode_var,
                                values=["silent", "normal", "fast"],
                                state="readonly", font=THEME["font_mono"])
        mode_box.pack(fill="x", pady=(2, 0))

        ttk.Separator(frame, orient="horizontal").pack(
            fill="x", padx=12, pady=10)

        # Module buttons
        tk.Label(frame, text="  MODULES", bg=THEME["bg"],
                 fg=THEME["fg_dim"],
                 font=(THEME["font_mono"][0], 9)).pack(anchor="w", padx=12)

        modules = [
            ("★  Auto Recon",            "auto",       "Accent.TButton"),
            ("   Port Scan",             "portscan",   "TButton"),
            ("   Web Crawl",             "crawl",      "TButton"),
            ("   Header Intelligence",   "headers",    "TButton"),
            ("   TLS Cert Enum",         "tls",        "TButton"),
            ("   CT Subdomain Enum",     "subdomains", "TButton"),
            ("   Reverse Proxy Detect",  "proxy",      "TButton"),
            ("   Deep Response Analyze", "body",       "TButton"),
            ("   DNS Lookup",            "dns",        "TButton"),
            ("   WHOIS Lookup",          "whois",      "TButton"),
            ("   IP Geolocation",        "geo",        "TButton"),
            ("   Robots + Sitemap",      "robots",     "TButton"),
            ("   Dork Generator",        "dorks",      "TButton"),
        ]
        self._mod_buttons = {}
        for label, key, style in modules:
            btn = ttk.Button(frame, text=label, style=style,
                             command=lambda k=key: self._run_module(k))
            btn.pack(fill="x", padx=12, pady=2)
            self._mod_buttons[key] = btn

        ttk.Separator(frame, orient="horizontal").pack(
            fill="x", padx=12, pady=10)

        # Stop button
        self._stop_btn = ttk.Button(frame, text="■  Stop",
                                    style="Danger.TButton",
                                    command=self._stop_run,
                                    state="disabled")
        self._stop_btn.pack(fill="x", padx=12, pady=2)

        return frame

    # ── Right panel — notebook ───────────────────────────────────
    def _build_right_panel(self):
        frame = tk.Frame(self, bg=THEME["bg"])

        nb = ttk.Notebook(frame)
        nb.pack(fill="both", expand=True)
        self._nb = nb

        # Tab 1: Terminal
        self._term_tab = tk.Frame(nb, bg=THEME["bg"])
        nb.add(self._term_tab, text="  Terminal  ")
        self._build_terminal(self._term_tab)

        # Tab 2: Findings
        self._find_tab = tk.Frame(nb, bg=THEME["bg"])
        nb.add(self._find_tab, text="  Findings  ")
        self._build_findings(self._find_tab)

        # Tab 3: Ports
        self._port_tab = tk.Frame(nb, bg=THEME["bg"])
        nb.add(self._port_tab, text="  Ports  ")
        self._build_ports(self._port_tab)

        # Tab 4: Subdomains
        self._sub_tab = tk.Frame(nb, bg=THEME["bg"])
        nb.add(self._sub_tab, text="  Subdomains  ")
        self._build_subdomains(self._sub_tab)

        # Tab 5: Raw JSON
        self._json_tab = tk.Frame(nb, bg=THEME["bg"])
        nb.add(self._json_tab, text="  Raw JSON  ")
        self._build_json_view(self._json_tab)

        return frame

    # ── Terminal tab ─────────────────────────────────────────────
    def _build_terminal(self, parent):
        self._term = scrolledtext.ScrolledText(
            parent,
            bg=THEME["bg"], fg=THEME["fg"],
            font=THEME["font_mono"],
            insertbackground=THEME["fg"],
            selectbackground=THEME["select"],
            relief="flat", borderwidth=0,
            wrap="word", state="disabled",
            padx=12, pady=8)
        self._term.pack(fill="both", expand=True)

        # Configure text tags
        for tag, color in LOG_TAG_COLORS.items():
            self._term.tag_configure(tag, foreground=color)
        self._term.tag_configure("TS",      foreground=THEME["fg_dim"])
        self._term.tag_configure("SECTION", foreground=THEME["blue"],
                                 font=(THEME["font_mono"][0], 11, "bold"))
        self._term.tag_configure("SEP",     foreground=THEME["border"])

    def _term_write(self, ts: str, tag: str, msg: str, color: str):
        self._term.configure(state="normal")
        self._term.insert("end", f"  [{ts}] ", "TS")
        self._term.insert("end", f"[{tag}]",
                          tag if tag in LOG_TAG_COLORS else "")
        self._term.insert("end", f" {msg}\n")
        self._term.configure(state="disabled")
        self._term.see("end")

    def _term_section(self, title: str):
        self._term.configure(state="normal")
        self._term.insert("end", f"\n  {'─'*52}\n", "SEP")
        self._term.insert("end", f"  {title}\n", "SECTION")
        self._term.configure(state="disabled")
        self._term.see("end")

    # ── Findings tab ─────────────────────────────────────────────
    def _build_findings(self, parent):
        cols = ("confidence", "type", "detail", "source")
        self._find_tree = ttk.Treeview(parent, columns=cols,
                                       show="headings", selectmode="browse")
        self._find_tree.heading("confidence", text="Level")
        self._find_tree.heading("type",       text="Type")
        self._find_tree.heading("detail",     text="Detail")
        self._find_tree.heading("source",     text="Source")
        self._find_tree.column("confidence", width=80,  minwidth=70, anchor="center")
        self._find_tree.column("type",       width=180, minwidth=120)
        self._find_tree.column("detail",     width=420, minwidth=200)
        self._find_tree.column("source",     width=200, minwidth=120)

        # Row colours by confidence
        self._find_tree.tag_configure("HIGH",   foreground=THEME["red"])
        self._find_tree.tag_configure("MEDIUM", foreground=THEME["yellow"])
        self._find_tree.tag_configure("LOW",    foreground=THEME["fg_dim"])

        sb = ttk.Scrollbar(parent, orient="vertical",
                           command=self._find_tree.yview)
        self._find_tree.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y")
        self._find_tree.pack(fill="both", expand=True)

    def _populate_findings(self, findings: list):
        for row in self._find_tree.get_children():
            self._find_tree.delete(row)
        for f in findings:
            conf = f.get("confidence", "LOW")
            self._find_tree.insert("", "end", values=(
                conf,
                f.get("type", "")[:30],
                f.get("detail", "")[:90],
                f.get("source", "")[:50],
            ), tags=(conf,))

    # ── Ports tab ────────────────────────────────────────────────
    def _build_ports(self, parent):
        cols = ("port", "service", "version", "tls")
        self._port_tree = ttk.Treeview(parent, columns=cols,
                                       show="headings", selectmode="browse")
        self._port_tree.heading("port",    text="Port")
        self._port_tree.heading("service", text="Service")
        self._port_tree.heading("version", text="Banner / Version")
        self._port_tree.heading("tls",     text="TLS")
        self._port_tree.column("port",    width=70,  anchor="center")
        self._port_tree.column("service", width=130)
        self._port_tree.column("version", width=400)
        self._port_tree.column("tls",     width=60,  anchor="center")

        self._port_tree.tag_configure("open", foreground=THEME["green"])
        self._port_tree.tag_configure("tls",  foreground=THEME["cyan"])

        sb = ttk.Scrollbar(parent, orient="vertical",
                           command=self._port_tree.yview)
        self._port_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._port_tree.pack(fill="both", expand=True)

    def _populate_ports(self, ports: list):
        for row in self._port_tree.get_children():
            self._port_tree.delete(row)
        for p in ports:
            tls = "✓" if p.get("tls") else "—"
            tag = "tls" if p.get("tls") else "open"
            self._port_tree.insert("", "end", values=(
                p["port"],
                p.get("service", "?"),
                p.get("version", "")[:80],
                tls,
            ), tags=(tag,))

    # ── Subdomains tab ───────────────────────────────────────────
    def _build_subdomains(self, parent):
        cols = ("host", "ip", "ports", "status")
        self._sub_tree = ttk.Treeview(parent, columns=cols,
                                      show="headings", selectmode="browse")
        self._sub_tree.heading("host",   text="Hostname")
        self._sub_tree.heading("ip",     text="IP Address")
        self._sub_tree.heading("ports",  text="Open Ports")
        self._sub_tree.heading("status", text="Flag")
        self._sub_tree.column("host",   width=320)
        self._sub_tree.column("ip",     width=140)
        self._sub_tree.column("ports",  width=80, anchor="center")
        self._sub_tree.column("status", width=80, anchor="center")

        self._sub_tree.tag_configure("hot",  foreground=THEME["red"])
        self._sub_tree.tag_configure("warn", foreground=THEME["yellow"])
        self._sub_tree.tag_configure("ok",   foreground=THEME["green"])

        sb = ttk.Scrollbar(parent, orient="vertical",
                           command=self._sub_tree.yview)
        self._sub_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._sub_tree.pack(fill="both", expand=True)

    def _populate_subdomains(self, subs: dict):
        for row in self._sub_tree.get_children():
            self._sub_tree.delete(row)
        for host, data in subs.items():
            n_ports = len(data.get("ports", []))
            n_err   = len(data.get("body", {}).get("errors", []))
            if n_err:
                flag, tag = "🔴 Error",  "hot"
            elif n_ports > 3:
                flag, tag = "🟡 Expose", "warn"
            else:
                flag, tag = "🟢 Clean",  "ok"
            self._sub_tree.insert("", "end", values=(
                host,
                data.get("ip", "?"),
                n_ports,
                flag,
            ), tags=(tag,))

    # ── Raw JSON tab ─────────────────────────────────────────────
    def _build_json_view(self, parent):
        self._json_text = scrolledtext.ScrolledText(
            parent,
            bg=THEME["bg2"], fg=THEME["cyan"],
            font=(THEME["font_mono"][0], 10),
            relief="flat", borderwidth=0,
            wrap="none", state="disabled",
            padx=12, pady=8)
        self._json_text.pack(fill="both", expand=True)

    def _populate_json(self, data: dict):
        self._json_text.configure(state="normal")
        self._json_text.delete("1.0", "end")
        self._json_text.insert("end",
            json.dumps(data, indent=2, default=str))
        self._json_text.configure(state="disabled")

    # ═══════════════════════════════════════════════════════════
    #  RUN LOGIC
    # ═══════════════════════════════════════════════════════════
    def _get_jitter(self):
        return engine.JitterEngine(self._mode_var.get())

    def _set_running(self, state: bool):
        self._running = state
        btn_state = "disabled" if state else "normal"
        for btn in self._mod_buttons.values():
            btn.configure(state=btn_state)
        self._stop_btn.configure(state="normal" if state else "disabled")
        if state:
            self._prog.start(12)
            self._status_var.set("Running…")
        else:
            self._prog.stop()
            self._status_var.set("Done")

    def _stop_run(self):
        self._running = False
        self._status_var.set("Stopped")
        self._prog.stop()
        for btn in self._mod_buttons.values():
            btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        gui_log("INFO", "Stopped by user", THEME["yellow"])

    def _run_module(self, key: str = "auto"):
        if self._running:
            return
        target = self._target_var.get().strip()
        if not target:
            messagebox.showwarning("ReconX", "Enter a target first")
            return

        self._clear_findings()
        self._set_running(True)
        jitter = self._get_jitter()
        ports  = self._ports_var.get().strip() or "common"

        def task():
            try:
                self._dispatch(key, target, jitter, ports)
            except Exception as exc:
                gui_log("ERR", str(exc), THEME["red"])
            finally:
                self.after(0, lambda: self._set_running(False))

        self._thread = threading.Thread(target=task, daemon=True)
        self._thread.start()

    def _dispatch(self, key: str, target: str, jitter, ports: str):
        host, ip = engine.resolve(target)
        if not ip:
            gui_log("ERR", f"Cannot resolve: {target}", THEME["red"])
            return

        result = {}

        if key == "auto":
            result = engine.auto_correlate(target, jitter, ports_input=ports)
            self._master_data = result
            self.after(0, lambda r=result: self._populate_all(r))
            engine.generate_html_report(result)

        elif key == "portscan":
            port_list = engine.parse_ports(ports)
            op, fl    = engine.run_scan(ip, port_list, host, jitter)
            result    = {"open": op, "filtered": fl}
            self.after(0, lambda o=op: self._populate_ports(o))
            self._nb.select(2)

        elif key == "crawl":
            result = engine.crawl(f"http://{host}", jitter=jitter)
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(4)

        elif key == "headers":
            result = engine.header_intelligence(f"http://{host}")
            findings = _headers_to_findings(result)
            self.after(0, lambda f=findings: self._populate_findings(f))
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(1)

        elif key == "tls":
            result = engine.tls_enum(host)
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(4)

        elif key == "subdomains":
            result = engine.ct_subdomain_enum(host)
            subs_dict = {e["host"]: {"ip": e["ip"], "ports": [], "body": {}}
                         for e in result.get("confirmed", [])}
            self.after(0, lambda s=subs_dict: self._populate_subdomains(s))
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(3)

        elif key == "proxy":
            result = engine.reverse_proxy_detect(host, ip)
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(4)

        elif key == "body":
            result = engine.deep_response_analyze(f"http://{host}")
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(4)

        elif key == "dns":
            result = engine.dns_lookup(host)
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(4)

        elif key == "whois":
            result = engine.whois_lookup(host)
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(4)

        elif key == "geo":
            result = engine.geoip(ip)
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(4)

        elif key == "robots":
            result = engine.harvest_robots_sitemap(f"http://{host}")
            self.after(0, lambda r=result: self._populate_json(r))
            self._nb.select(4)

        elif key == "dorks":
            result = engine.dork_generator(host, auto_open=False)
            self.after(0, lambda r=result: self._populate_json({"dorks": r}))
            self._nb.select(4)

        self._master_data = result

    def _populate_all(self, master: dict):
        """Populate all tabs from auto_correlate master dict."""
        self._populate_findings(master.get("all_findings", []))
        primary = master.get("primary", {})
        self._populate_ports(primary.get("ports", []))
        self._populate_subdomains(master.get("subdomains", {}))
        self._populate_json(master)

    def _clear_findings(self):
        for row in self._find_tree.get_children():
            self._find_tree.delete(row)
        for row in self._port_tree.get_children():
            self._port_tree.delete(row)
        for row in self._sub_tree.get_children():
            self._sub_tree.delete(row)

    # ═══════════════════════════════════════════════════════════
    #  QUEUE POLLING — pull logs from worker thread into GUI
    # ═══════════════════════════════════════════════════════════
    def _poll_queues(self):
        # Process up to 50 log items per poll tick
        for _ in range(50):
            try:
                item = log_queue.get_nowait()
                if item[0] == "log":
                    _, ts, tag, msg, color = item
                    self._term_write(ts, tag, msg, color)
                elif item[0] == "section":
                    self._term_section(item[1])
            except queue.Empty:
                break

        # Schedule next poll
        self.after(80, self._poll_queues)

    # ═══════════════════════════════════════════════════════════
    #  FILE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    def _save_json(self):
        if not self._master_data:
            messagebox.showinfo("ReconX", "Run a module first")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if path:
            Path("recon_output").mkdir(exist_ok=True)
            with open(path, "w") as f:
                json.dump(self._master_data, f, indent=2, default=str)
            gui_log("SAVED", f"→ {path}", THEME["purple"])

    def _save_html(self):
        if not self._master_data:
            messagebox.showinfo("ReconX", "Run Auto Recon first for HTML report")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML", "*.html"), ("All", "*.*")])
        if path:
            engine.generate_html_report(self._master_data, out_path=path)

    def _clear_terminal(self):
        self._term.configure(state="normal")
        self._term.delete("1.0", "end")
        self._term.configure(state="disabled")

    def _show_about(self):
        messagebox.showinfo("About ReconX",
            "ReconX v3\nRecon & Intelligence Suite\n\n"
            "Built by Faizan\ngithub.com/faizu526\n\n"
            "Use only on systems you own\nor have explicit written permission to test.")


# ═══════════════════════════════════════════════════════════════
#  HELPER — convert header_intelligence dict → findings list
# ═══════════════════════════════════════════════════════════════
def _headers_to_findings(hdr: dict) -> list:
    out = []
    for item in hdr.get("dangerous", []):
        out.append({"confidence":"HIGH","type":"DANGEROUS_HEADER",
                    "detail":item["note"],"source":item["header"]})
    for item in hdr.get("missing_sec", []):
        out.append({"confidence":"MEDIUM","type":"MISSING_SEC_HEADER",
                    "detail":item["note"],"source":item["header"]})
    for item in hdr.get("stack", []):
        out.append({"confidence":"LOW","type":"STACK_DISCLOSURE",
                    "detail":f"{item['tech']}: {item['value'][:50]}",
                    "source":item["header"]})
    return out


# ═══════════════════════════════════════════════════════════════
#  ENTRY
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = ReconXApp()
    app.mainloop()
