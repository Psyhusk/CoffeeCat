#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════╗
║           CoffeeCat — Linux Rescue Toolkit                ║
║     Installs a bootable maintenance environment           ║
║     onto USB drives with a Neobank-style dark UI          ║
╚═══════════════════════════════════════════════════════════╝

Requirements (install before running):
  pip install customtkinter psutil

  System tools needed (installed separately):
  - dd / pv           -> write ISO to USB
  - lsblk / fdisk     -> disk detection
  - grub-install      -> bootloader repair
  - chroot            -> system recovery
  - smartmontools     -> disk health (smartctl)
  - wget / curl       -> download ISO
  - lscpu / dmidecode -> CPU / hardware info
"""

import os
import sys
import json
import time
import re
import subprocess
import threading
from pathlib import Path
from datetime import datetime

# ─── GUI dependencies ─────────────────────────────────────
try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog
except ImportError:
    print("[!] customtkinter not found. Install with:\n    pip install customtkinter")
    sys.exit(1)

try:
    import psutil
except ImportError:
    psutil = None

# ══════════════════════════════════════════════════════════
#  THEME  — Carbon / C6 Bank inspired palette
# ══════════════════════════════════════════════════════════
T = {
    "bg":          "#0D0D0D",
    "card":        "#181818",
    "card_hov":    "#202020",
    "border":      "#2A2A2A",
    "accent":      "#F5C518",
    "accent2":     "#E07B00",
    "success":     "#22C55E",
    "danger":      "#EF4444",
    "warning":     "#F59E0B",
    "text":        "#F0F0F0",
    "muted":       "#7A7A7A",
    "input":       "#141414",
    "sidebar":     "#111111",
    "mono_fg":     "#A3E635",
    "mono_bg":     "#0A0A0A",
}

F_TITLE = ("Helvetica", 22, "bold")
F_HEAD  = ("Helvetica", 14, "bold")
F_BODY  = ("Helvetica", 12)
F_SM    = ("Helvetica", 10)
F_MONO  = ("Courier New", 10)

VERSION  = "1.0.0"


# ══════════════════════════════════════════════════════════
#  COMMAND RUNNER
# ══════════════════════════════════════════════════════════

class CMD:
    @staticmethod
    def run(cmd, timeout=None):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=timeout)
            return r.returncode == 0, (r.stdout + r.stderr).strip()
        except Exception as e:
            return False, str(e)

    @staticmethod
    def stream(cmd, cb=None):
        try:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
            for line in iter(proc.stdout.readline, ""):
                if cb:
                    cb(line.rstrip())
            proc.wait()
            return proc.returncode == 0
        except Exception as e:
            if cb:
                cb(f"[ERROR] {e}")
            return False

    @staticmethod
    def is_root():
        return os.geteuid() == 0


# ══════════════════════════════════════════════════════════
#  HARDWARE
# ══════════════════════════════════════════════════════════

class HW:
    @staticmethod
    def cpu():
        info = {"model": "Unknown", "cores": "?", "threads": "?",
                "usage": "?", "temp": "N/A"}
        ok, out = CMD.run("lscpu")
        if ok:
            for ln in out.splitlines():
                if "Model name" in ln:
                    info["model"] = ln.split(":", 1)[1].strip()
                if re.match(r"^CPU\(s\):", ln):
                    info["threads"] = ln.split(":")[1].strip()
                if "Core(s) per socket" in ln:
                    info["cores"] = ln.split(":")[1].strip()
        if psutil:
            info["usage"] = f"{psutil.cpu_percent(interval=0.5):.0f}%"
            try:
                temps = psutil.sensors_temperatures()
                for k in ("coretemp", "k10temp", "cpu_thermal"):
                    if k in temps:
                        info["temp"] = f"{temps[k][0].current:.0f}°C"
                        break
            except Exception:
                pass
        return info

    @staticmethod
    def mem():
        info = {"total": "?", "used": "?", "free": "?", "pct": "?"}
        if psutil:
            m = psutil.virtual_memory()
            info["total"] = f"{m.total/1e9:.1f} GB"
            info["used"]  = f"{m.used/1e9:.1f} GB"
            info["free"]  = f"{m.available/1e9:.1f} GB"
            info["pct"]   = f"{m.percent:.0f}%"
        else:
            ok, out = CMD.run("free -h")
            if ok:
                parts = out.splitlines()[1].split() if len(out.splitlines()) > 1 else []
                if len(parts) >= 3:
                    info["total"] = parts[1]
                    info["used"]  = parts[2]
                    info["free"]  = parts[3] if len(parts) > 3 else "?"
        return info

    @staticmethod
    def disks():
        result = []
        ok, out = CMD.run(
            "lsblk -J -o NAME,SIZE,TYPE,MOUNTPOINT,VENDOR,MODEL,TRAN,RM 2>/dev/null")
        if ok:
            try:
                for dev in json.loads(out).get("blockdevices", []):
                    if dev.get("type") == "disk":
                        result.append({
                            "name":  f"/dev/{dev['name']}",
                            "size":  dev.get("size", "?"),
                            "model": f"{dev.get('vendor','')}{dev.get('model','')}".strip(),
                            "tran":  dev.get("tran", ""),
                            "rm":    dev.get("rm", False) in (True, "1", 1),
                        })
            except Exception:
                pass
        return result

    @staticmethod
    def smart(dev):
        info = {"status": "N/A", "reallocated": "?", "hours": "?", "temp": "?"}
        ok, out = CMD.run(f"smartctl -A {dev} 2>/dev/null")
        if ok:
            for ln in out.splitlines():
                if "Reallocated_Sector" in ln:
                    info["reallocated"] = ln.split()[-1]
                if "Power_On_Hours" in ln:
                    info["hours"] = ln.split()[-1] + "h"
                if "Temperature_Celsius" in ln:
                    info["temp"] = ln.split()[-1] + "°C"
            info["status"] = "OK" if "PASSED" in out else "WARN"
        return info

    @staticmethod
    def linux_parts():
        parts = []
        ok, out = CMD.run(
            "lsblk -J -o NAME,FSTYPE,LABEL,SIZE,MOUNTPOINT 2>/dev/null")
        if ok:
            def walk(devs):
                for d in devs:
                    fs = d.get("fstype") or ""
                    if fs in ("ext4", "ext3", "btrfs", "xfs", "f2fs"):
                        parts.append({
                            "device": f"/dev/{d['name']}",
                            "fstype": fs,
                            "size":   d.get("size", "?"),
                        })
                    walk(d.get("children", []))
            try:
                walk(json.loads(out).get("blockdevices", []))
            except Exception:
                pass
        return parts


# ══════════════════════════════════════════════════════════
#  RECOVERY
# ══════════════════════════════════════════════════════════

CHROOT = "/mnt/coffeecat_chroot"


def mount_chroot(device, cb=None):
    for cmd in [
        f"mkdir -p {CHROOT}",
        f"mount {device} {CHROOT}",
        f"mount --bind /dev  {CHROOT}/dev",
        f"mount --bind /proc {CHROOT}/proc",
        f"mount --bind /sys  {CHROOT}/sys",
    ]:
        if cb: cb(f"$ {cmd}")
        ok, out = CMD.run(cmd)
        if cb and out: cb(out)
        if not ok and "already mounted" not in out.lower():
            return False
    return True


def umount_chroot(cb=None):
    for sub in ("dev", "proc", "sys", ""):
        p = f"{CHROOT}/{sub}".rstrip("/")
        cmd = f"umount {p} 2>/dev/null"
        if cb: cb(f"$ {cmd}")
        CMD.run(cmd)


def repair_grub(disk, cb=None):
    for cmd in [
        f"chroot {CHROOT} grub-install {disk}",
        f"chroot {CHROOT} update-grub",
    ]:
        if cb: cb(f"$ {cmd}")
        if not CMD.stream(cmd, cb):
            return False
    return True


def reset_password(user, pw, cb=None):
    cmd = f"echo '{user}:{pw}' | chroot {CHROOT} chpasswd"
    if cb: cb("$ chpasswd [redacted]")
    ok, out = CMD.run(cmd)
    if cb and out: cb(out)
    return ok


# ══════════════════════════════════════════════════════════
#  USB INSTALLER
# ══════════════════════════════════════════════════════════

def write_iso(iso, device, prog_cb=None, log_cb=None):
    ok, out = CMD.run(f"findmnt {device}")
    if ok and out:
        if log_cb: log_cb(f"[ERROR] {device} está montado! Recusando.")
        return False

    size = Path(iso).stat().st_size
    pv_ok, _ = CMD.run("which pv")
    if pv_ok:
        cmd = f"pv -n -s {size} '{iso}' | dd of='{device}' bs=4M conv=fsync 2>&1"
    else:
        cmd = f"dd if='{iso}' of='{device}' bs=4M conv=fsync status=progress 2>&1"

    if log_cb: log_cb(f"Gravando {iso} → {device} …")

    def _parse(ln):
        if log_cb: log_cb(ln)
        if prog_cb and ln.strip().isdigit():
            prog_cb(int(ln.strip()))

    ok = CMD.stream(cmd, _parse)
    if ok:
        CMD.run("sync")
        if log_cb: log_cb("[OK] Gravação concluída.")
    return ok


def download_iso(url, dest_dir, prog_cb=None, log_cb=None):
    fname = url.split("/")[-1].split("?")[0]
    dest  = str(Path(dest_dir) / fname)
    cmd   = f"wget -c --progress=dot:mega '{url}' -O '{dest}' 2>&1"
    if log_cb: log_cb(f"Baixando: {url}")

    def _parse(ln):
        if log_cb: log_cb(ln)
        m = re.search(r"(\d+)%", ln)
        if m and prog_cb: prog_cb(int(m.group(1)))

    return dest if CMD.stream(cmd, _parse) else None


# ══════════════════════════════════════════════════════════
#  UI WIDGETS
# ══════════════════════════════════════════════════════════

class Card(ctk.CTkFrame):
    """Hoverable action card."""
    def __init__(self, master, icon, title, subtitle="", command=None, **kw):
        super().__init__(master, fg_color=T["card"], corner_radius=14,
                         border_width=1, border_color=T["border"], **kw)
        self.command = command

        ctk.CTkLabel(self, text=icon, font=("Segoe UI Emoji", 28),
                     text_color=T["accent"]).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(self, text=title, font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=20)
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=F_SM,
                         text_color=T["muted"], wraplength=200).pack(
                anchor="w", padx=20, pady=(2, 14))

        for w in (self, *self.winfo_children()):
            w.bind("<Enter>", lambda _: self.configure(
                fg_color=T["card_hov"], border_color=T["accent"]))
            w.bind("<Leave>", lambda _: self.configure(
                fg_color=T["card"], border_color=T["border"]))
            w.bind("<Button-1>", lambda _: self.command() if self.command else None)


class LogBox(ctk.CTkFrame):
    """Collapsible terminal console."""
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=T["bg"], **kw)
        self._open = False

        hdr = ctk.CTkFrame(self, fg_color=T["card"], corner_radius=8, height=36)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="▸  Terminal", font=F_SM,
                     text_color=T["muted"]).pack(side="left", padx=12)
        self._btn = ctk.CTkButton(
            hdr, text="Mostrar ▾", width=80, height=26,
            fg_color="transparent", hover_color=T["border"],
            text_color=T["accent"], font=F_SM, command=self._toggle)
        self._btn.pack(side="right", padx=8)

        self._tb = ctk.CTkTextbox(self, height=160, font=F_MONO,
                                   fg_color=T["mono_bg"], text_color=T["mono_fg"],
                                   corner_radius=0)

    def _toggle(self):
        self._open = not self._open
        if self._open:
            self._tb.pack(fill="x")
            self._btn.configure(text="Ocultar ▴")
        else:
            self._tb.pack_forget()
            self._btn.configure(text="Mostrar ▾")

    def log(self, text):
        def _do():
            self._tb.configure(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self._tb.insert("end", f"[{ts}] {text}\n")
            self._tb.see("end")
            self._tb.configure(state="disabled")
        try:
            self._tb.after(0, _do)
        except Exception:
            pass


class ProgCard(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=T["card"], corner_radius=14, **kw)
        self._lbl = ctk.CTkLabel(self, text="Aguardando…", font=F_BODY,
                                  text_color=T["muted"])
        self._lbl.pack(anchor="w", padx=20, pady=(14, 4))
        self._bar = ctk.CTkProgressBar(self, height=6,
                                        fg_color=T["border"],
                                        progress_color=T["accent"])
        self._bar.set(0)
        self._bar.pack(fill="x", padx=20, pady=(0, 14))

    def update(self, label, pct):
        self._lbl.configure(text=label)
        self._bar.set(pct / 100)

    def reset(self, label="Aguardando…"):
        self._lbl.configure(text=label)
        self._bar.set(0)


def badge(parent, text, status="info"):
    colors = {
        "ok":   (T["success"], "#052e16"),
        "err":  (T["danger"],  "#2d0a0a"),
        "warn": (T["warning"], "#2d1a00"),
        "info": (T["accent"],  "#2d2000"),
    }
    fg, bg = colors.get(status, colors["info"])
    return ctk.CTkLabel(parent, text=f"  {text}  ", font=F_SM,
                        text_color=fg, fg_color=bg, corner_radius=20)


def sep(parent):
    ctk.CTkFrame(parent, height=1, fg_color=T["border"]).pack(
        fill="x", padx=32, pady=(4, 16))


# ══════════════════════════════════════════════════════════
#  APPLICATION
# ══════════════════════════════════════════════════════════

class CoffeeCat(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(f"CoffeeCat v{VERSION}")
        self.geometry("1080x740")
        self.minsize(900, 620)
        self.configure(fg_color=T["bg"])

        self._cache = {}
        self._build_layout()
        self._nav_to(self._dash, "Dashboard")
        threading.Thread(target=self._bg_scan, daemon=True).start()

    # ── skeleton ──────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._sidebar = self._mk_sidebar()
        self._sidebar.grid(row=0, column=0, sticky="nsw")
        self._pane = ctk.CTkFrame(self, fg_color=T["bg"], corner_radius=0)
        self._pane.grid(row=0, column=1, sticky="nsew")
        self._pane.grid_columnconfigure(0, weight=1)
        self._pane.grid_rowconfigure(0, weight=1)

    def _mk_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=T["sidebar"], width=224, corner_radius=0)
        sb.pack_propagate(False)

        # brand
        logo = ctk.CTkFrame(sb, fg_color="transparent", height=80)
        logo.pack(fill="x")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="☕", font=("Segoe UI Emoji", 30),
                     text_color=T["accent"]).place(x=20, y=20)
        ctk.CTkLabel(logo, text="CoffeeCat", font=F_TITLE,
                     text_color=T["text"]).place(x=60, y=24)
        ctk.CTkFrame(sb, height=1, fg_color=T["border"]).pack(fill="x")

        navs = [
            ("🏠", "Dashboard",     self._dash),
            ("🔬", "Hardware",      self._hw_page),
            ("💿", "USB Installer", self._usb_page),
            ("🛠", "Recovery",      self._rec_page),
            ("📋", "Logs",          self._logs_page),
        ]
        self._nav_btns = {}
        for icon, label, fn in navs:
            b = ctk.CTkButton(
                sb, text=f"  {icon}  {label}", anchor="w",
                height=44, corner_radius=0,
                fg_color="transparent", hover_color=T["card"],
                text_color=T["muted"], font=F_BODY,
                command=lambda f=fn, l=label: self._nav_to(f, l)
            )
            b.pack(fill="x", pady=1)
            self._nav_btns[label] = b

        ctk.CTkFrame(sb, fg_color="transparent").pack(expand=True)
        ctk.CTkFrame(sb, height=1, fg_color=T["border"]).pack(fill="x")
        root_txt   = "● root" if CMD.is_root() else "⚠ no root"
        root_color = T["success"] if CMD.is_root() else T["warning"]
        ctk.CTkLabel(sb, text=root_txt, font=F_SM,
                     text_color=root_color).pack(anchor="w", padx=20, pady=10)
        return sb

    def _nav_to(self, fn, label):
        for lbl, btn in self._nav_btns.items():
            if lbl == label:
                btn.configure(text_color=T["accent"], fg_color=T["card"])
            else:
                btn.configure(text_color=T["muted"], fg_color="transparent")
        fn()

    def _clear(self):
        for w in self._pane.winfo_children():
            w.destroy()

    def _scroll(self):
        sf = ctk.CTkScrollableFrame(self._pane, fg_color=T["bg"], corner_radius=0)
        sf.grid(row=0, column=0, sticky="nsew")
        sf.grid_columnconfigure(0, weight=1)
        return sf

    def _header(self, parent, title, sub=""):
        h = ctk.CTkFrame(parent, fg_color="transparent")
        h.pack(fill="x", padx=32, pady=(28, 8))
        ctk.CTkLabel(h, text=title, font=F_TITLE, text_color=T["text"]).pack(anchor="w")
        if sub:
            ctk.CTkLabel(h, text=sub, font=F_SM, text_color=T["muted"]).pack(
                anchor="w", pady=(2, 0))
        sep(parent)

    # ── Dashboard ─────────────────────────────────────────

    def _dash(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "Dashboard", "Visão geral e ações rápidas")

        # status badges
        row = ctk.CTkFrame(sf, fg_color="transparent")
        row.pack(fill="x", padx=32, pady=(0, 12))
        badge(row, "root" if CMD.is_root() else "sem root",
              "ok" if CMD.is_root() else "warn").pack(side="left", padx=(0, 6))
        for tool, name in [("pv", "pv"), ("smartctl", "smartctl"),
                           ("grub-install", "grub")]:
            ok, _ = CMD.run(f"which {tool}")
            badge(row, f"{name} ✓" if ok else f"{name} ausente",
                  "ok" if ok else "warn").pack(side="left", padx=(0, 6))

        # cards
        g = ctk.CTkFrame(sf, fg_color="transparent")
        g.pack(fill="x", padx=28, pady=8)
        g.grid_columnconfigure((0, 1, 2), weight=1, uniform="c")
        items = [
            ("💿", "USB Installer", "Gravar ISO no pendrive",
             lambda: self._nav_to(self._usb_page, "USB Installer")),
            ("🔬", "Hardware", "Diagnóstico em tempo real",
             lambda: self._nav_to(self._hw_page, "Hardware")),
            ("🛠", "Recovery", "Chroot · GRUB · Senhas",
             lambda: self._nav_to(self._rec_page, "Recovery")),
        ]
        for i, (ic, tl, st, cmd) in enumerate(items):
            Card(g, ic, tl, st, cmd).grid(row=0, column=i, padx=8, pady=8, sticky="nsew")

        # metrics
        ctk.CTkLabel(sf, text="Métricas ao vivo", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=32, pady=(16, 4))
        self._dash_hw = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=14)
        self._dash_hw.pack(fill="x", padx=32, pady=(0, 8))
        ctk.CTkLabel(self._dash_hw, text="Escaneando…", font=F_SM,
                     text_color=T["muted"]).pack(pady=16)

        ctk.CTkLabel(sf, text="Discos detectados", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=32, pady=(8, 4))
        self._dash_disks = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=14)
        self._dash_disks.pack(fill="x", padx=32, pady=(0, 28))
        ctk.CTkLabel(self._dash_disks, text="Escaneando…", font=F_SM,
                     text_color=T["muted"]).pack(pady=16)

        self.after(1400, self._fill_dash)

    def _fill_dash(self):
        if not self._cache:
            self.after(600, self._fill_dash); return
        try:
            # hw metrics
            for w in self._dash_hw.winfo_children(): w.destroy()
            cpu = self._cache.get("cpu", {})
            mem = self._cache.get("mem", {})
            row = ctk.CTkFrame(self._dash_hw, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=16)
            for lbl, val in [
                ("CPU",    cpu.get("model", "?")[:30]),
                ("Cores",  cpu.get("cores", "?")),
                ("Uso",    cpu.get("usage", "?")),
                ("Temp",   cpu.get("temp", "?")),
                ("RAM",    mem.get("total", "?")),
                ("Usada",  mem.get("used", "?")),
                ("Livre",  mem.get("free", "?")),
            ]:
                c = ctk.CTkFrame(row, fg_color=T["bg"], corner_radius=8)
                c.pack(side="left", padx=5, ipadx=10, ipady=4)
                ctk.CTkLabel(c, text=lbl, font=F_SM, text_color=T["muted"]).pack()
                ctk.CTkLabel(c, text=val, font=F_BODY, text_color=T["accent"]).pack()

            # disks
            for w in self._dash_disks.winfo_children(): w.destroy()
            for d in self._cache.get("disks", []):
                dr = ctk.CTkFrame(self._dash_disks, fg_color=T["bg"], corner_radius=8)
                dr.pack(fill="x", padx=16, pady=4)
                tag = "  🔌 USB" if (d.get("rm") or d.get("tran") == "usb") else ""
                ctk.CTkLabel(dr, text=f"{d['name']}  {d['size']}  {d['model']}{tag}",
                             font=F_BODY, text_color=T["text"]).pack(
                    side="left", padx=12, pady=8)
        except Exception:
            pass

    def _bg_scan(self):
        self._cache = {
            "cpu":   HW.cpu(),
            "mem":   HW.mem(),
            "disks": HW.disks(),
        }

    # ── Hardware ──────────────────────────────────────────

    def _hw_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "Hardware", "CPU · RAM · Discos · SMART")

        ctk.CTkButton(sf, text="⟳  Atualizar Scan", width=160, height=36,
                      fg_color=T["accent"], text_color="#000",
                      hover_color=T["accent2"], font=F_BODY, corner_radius=8,
                      command=lambda: threading.Thread(
                          target=self._do_hw, args=(body,), daemon=True).start()
                      ).pack(anchor="w", padx=32, pady=(0, 8))

        body = ctk.CTkFrame(sf, fg_color="transparent")
        body.pack(fill="x", padx=32)
        threading.Thread(target=self._do_hw, args=(body,), daemon=True).start()

    def _do_hw(self, c):
        def post(fn): c.after(0, fn)
        def clear():
            for w in c.winfo_children(): w.destroy()
        def section(title):
            def _():
                ctk.CTkLabel(c, text=title, font=F_HEAD,
                             text_color=T["accent"]).pack(anchor="w", pady=(14, 4))
            post(_)
        def row(lbl, val, ok=None):
            def _():
                r = ctk.CTkFrame(c, fg_color=T["card"], corner_radius=8, height=38)
                r.pack(fill="x", pady=2)
                r.pack_propagate(False)
                ctk.CTkLabel(r, text=lbl, font=F_SM, text_color=T["muted"],
                             width=200, anchor="w").pack(side="left", padx=12)
                col = T["text"]
                if ok is True:  col = T["success"]
                if ok is False: col = T["danger"]
                ctk.CTkLabel(r, text=str(val), font=F_BODY,
                             text_color=col).pack(side="left")
            post(_)

        post(clear)
        cpu = HW.cpu()
        section("⚙  CPU")
        for k, v in [("Modelo", cpu["model"]), ("Cores", cpu["cores"]),
                     ("Threads", cpu["threads"]), ("Uso", cpu["usage"]),
                     ("Temperatura", cpu["temp"])]:
            row(k, v)

        mem = HW.mem()
        section("🧠  Memória")
        for k, v in [("Total", mem["total"]), ("Usada", mem["used"]),
                     ("Livre", mem["free"]), ("Uso %", mem["pct"])]:
            row(k, v)

        section("💾  Discos")
        for d in HW.disks():
            row(d["name"], f"{d['size']}  {d['model']}  [{d.get('tran','')}]")
            s = HW.smart(d["name"])
            row("  └ SMART", s["status"], ok=s["status"] == "OK")
            row("  └ Setores realocados", s["reallocated"])
            row("  └ Horas ligado", s["hours"])
            row("  └ Temperatura", s["temp"])

    # ── USB Installer ─────────────────────────────────────

    def _usb_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "USB Installer", "Grave uma ISO de recuperação no pendrive")

        if not CMD.is_root():
            ctk.CTkLabel(sf, text="⚠  Execute como root (sudo) para gravar no disco.",
                         font=F_BODY, text_color=T["warning"]).pack(
                anchor="w", padx=32, pady=(0, 8))

        # Source card
        src = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=14)
        src.pack(fill="x", padx=32, pady=6)
        ctk.CTkLabel(src, text="Origem da ISO", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=20, pady=(16, 8))

        tab = ctk.CTkTabview(src, height=130,
                              fg_color=T["input"],
                              segmented_button_fg_color=T["border"],
                              segmented_button_selected_color=T["accent"],
                              segmented_button_selected_hover_color=T["accent2"],
                              segmented_button_unselected_color=T["border"],
                              text_color=T["text"])
        tab.pack(fill="x", padx=20, pady=(0, 16))
        tab.add("📂  Local")
        tab.add("🌐  Download")

        # local
        self._iso_var = ctk.StringVar()
        lr = ctk.CTkFrame(tab.tab("📂  Local"), fg_color="transparent")
        lr.pack(fill="x", pady=10)
        ctk.CTkEntry(lr, textvariable=self._iso_var,
                     placeholder_text="Caminho para .iso…",
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=36,
                     width=360).pack(side="left", padx=(8, 6))
        ctk.CTkButton(lr, text="Procurar", width=100, height=36,
                      fg_color=T["border"], hover_color=T["card_hov"],
                      text_color=T["text"], font=F_SM, corner_radius=8,
                      command=self._browse).pack(side="left")

        # download
        self._url_var = ctk.StringVar(
            value="https://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso")
        dr = ctk.CTkFrame(tab.tab("🌐  Download"), fg_color="transparent")
        dr.pack(fill="x", pady=10)
        ctk.CTkEntry(dr, textvariable=self._url_var,
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=36,
                     width=460).pack(side="left", padx=8)

        # Target
        tgt = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=14)
        tgt.pack(fill="x", padx=32, pady=6)
        ctk.CTkLabel(tgt, text="Pendrive de destino", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=20, pady=(16, 8))
        tr = ctk.CTkFrame(tgt, fg_color="transparent")
        tr.pack(fill="x", padx=20, pady=(0, 16))
        self._usb_var = ctk.StringVar()
        self._usb_menu = ctk.CTkOptionMenu(
            tr, variable=self._usb_var, values=["(detectando…)"],
            fg_color=T["input"], button_color=T["border"],
            button_hover_color=T["accent"], text_color=T["text"],
            font=F_BODY, width=280)
        self._usb_menu.pack(side="left", padx=(0, 8))
        ctk.CTkButton(tr, text="↺", width=36, height=36,
                      fg_color=T["border"], hover_color=T["accent"],
                      text_color=T["text"], font=F_HEAD, corner_radius=8,
                      command=self._refresh_usbs).pack(side="left")

        # progress + log
        self._usb_prog = ProgCard(sf)
        self._usb_prog.pack(fill="x", padx=32, pady=6)
        self._usb_log = LogBox(sf)
        self._usb_log.pack(fill="x", padx=32, pady=4)

        ctk.CTkButton(sf, text="✦  Gravar no Pendrive", height=48,
                      fg_color=T["accent"], text_color="#000",
                      hover_color=T["accent2"], font=F_HEAD, corner_radius=12,
                      command=lambda: threading.Thread(
                          target=self._do_write, args=(tab,), daemon=True).start()
                      ).pack(fill="x", padx=32, pady=(8, 28))

        self._refresh_usbs()

    def _browse(self):
        p = filedialog.askopenfilename(
            filetypes=[("ISO images", "*.iso"), ("All files", "*.*")])
        if p: self._iso_var.set(p)

    def _refresh_usbs(self):
        disks = HW.disks()
        entries = []
        for d in disks:
            tag = " [USB]" if (d.get("rm") or d.get("tran") == "usb") else ""
            entries.append(f"{d['name']}  {d['size']}{tag}")
        if not entries: entries = ["(nenhum disco)"]
        self._usb_menu.configure(values=entries)
        self._usb_var.set(entries[0])

    def _do_write(self, tab):
        log = self._usb_log.log
        prog = lambda p: self._usb_prog.update(f"Gravando… {p}%", p)
        iso  = None

        if "Local" in tab.get():
            iso = self._iso_var.get().strip()
            if not iso or not Path(iso).exists():
                log("[!] ISO inválida ou não encontrada."); return
            log(f"ISO: {iso}  ({Path(iso).stat().st_size/1e6:.0f} MB)")
        else:
            url = self._url_var.get().strip()
            if not url: log("[!] URL vazia."); return
            iso = download_iso(url, str(Path.home() / "Downloads"), prog, log)
            if not iso: log("[!] Download falhou."); return

        device = self._usb_var.get().split()[0]
        if not device.startswith("/dev/"):
            log("[!] Dispositivo inválido."); return

        # confirm
        confirmed = [False]
        def ask():
            confirmed[0] = messagebox.askyesno(
                "Confirmar",
                f"⚠ TODOS OS DADOS em {device} serão APAGADOS permanentemente!\n\n"
                f"ISO:     {iso}\nDestino: {device}\n\nContinuar?")
        self.after(0, ask)
        time.sleep(0.5)
        if not confirmed[0]:
            log("Operação cancelada."); return

        self._usb_prog.update("Iniciando…", 0)
        ok = write_iso(iso, device, prog, log)
        if ok:
            self._usb_prog.update("Concluído! ✓", 100)
            self.after(0, lambda: messagebox.showinfo(
                "CoffeeCat", "✓ Pendrive criado com sucesso!\nEle está pronto para uso."))
        else:
            self._usb_prog.reset("Falha!")
            log("[!] Gravação falhou. Verifique permissões (root) e o dispositivo.")

    # ── Recovery ──────────────────────────────────────────

    def _rec_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "Recovery", "Chroot · GRUB · Reset de Senha")

        if not CMD.is_root():
            ctk.CTkLabel(sf, text="⚠  Root necessário para operações de recuperação.",
                         font=F_BODY, text_color=T["warning"]).pack(
                anchor="w", padx=32, pady=(0, 8))

        # partition
        pc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=14)
        pc.pack(fill="x", padx=32, pady=6)
        ctk.CTkLabel(pc, text="Partição Linux", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=20, pady=(16, 8))
        pr = ctk.CTkFrame(pc, fg_color="transparent")
        pr.pack(fill="x", padx=20, pady=(0, 16))
        self._part_var = ctk.StringVar()
        self._part_menu = ctk.CTkOptionMenu(
            pr, variable=self._part_var, values=["(detectando…)"],
            fg_color=T["input"], button_color=T["border"],
            button_hover_color=T["accent"], text_color=T["text"],
            font=F_BODY, width=300)
        self._part_menu.pack(side="left", padx=(0, 8))
        ctk.CTkButton(pr, text="↺ Detectar", width=110, height=36,
                      fg_color=T["border"], hover_color=T["accent"],
                      text_color=T["text"], font=F_SM, corner_radius=8,
                      command=self._refresh_parts).pack(side="left")

        # ops grid
        g = ctk.CTkFrame(sf, fg_color="transparent")
        g.pack(fill="x", padx=28, pady=8)
        g.grid_columnconfigure((0, 1), weight=1, uniform="op")

        # GRUB
        gc = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=14)
        gc.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(gc, text="🔧  Reparar GRUB", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(gc, text="Re-instala o bootloader no disco alvo.",
                     font=F_SM, text_color=T["muted"], wraplength=220).pack(
            anchor="w", padx=20)
        grub_dsk = ctk.StringVar(value="/dev/sda")
        ctk.CTkEntry(gc, textvariable=grub_dsk,
                     placeholder_text="Disco alvo (ex: /dev/sda)",
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=34).pack(
            fill="x", padx=20, pady=8)
        ctk.CTkButton(gc, text="Reparar GRUB", height=36,
                      fg_color=T["accent"], text_color="#000",
                      hover_color=T["accent2"], font=F_BODY, corner_radius=8,
                      command=lambda: threading.Thread(
                          target=self._do_grub, args=(grub_dsk.get(),),
                          daemon=True).start()
                      ).pack(fill="x", padx=20, pady=(0, 16))

        # Password
        pwc = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=14)
        pwc.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(pwc, text="🔑  Reset de Senha", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(pwc, text="Altera a senha de um usuário via chroot.",
                     font=F_SM, text_color=T["muted"], wraplength=220).pack(
            anchor="w", padx=20)
        usr_var = ctk.StringVar()
        pw_var  = ctk.StringVar()
        ctk.CTkEntry(pwc, textvariable=usr_var,
                     placeholder_text="Usuário (ex: ubuntu)",
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=34).pack(
            fill="x", padx=20, pady=(8, 4))
        ctk.CTkEntry(pwc, textvariable=pw_var,
                     placeholder_text="Nova senha",
                     show="●", font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=34).pack(
            fill="x", padx=20, pady=(0, 8))
        ctk.CTkButton(pwc, text="Resetar Senha", height=36,
                      fg_color=T["accent"], text_color="#000",
                      hover_color=T["accent2"], font=F_BODY, corner_radius=8,
                      command=lambda: threading.Thread(
                          target=self._do_pw,
                          args=(usr_var.get(), pw_var.get()),
                          daemon=True).start()
                      ).pack(fill="x", padx=20, pady=(0, 16))

        # manual chroot
        mc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=14)
        mc.pack(fill="x", padx=32, pady=6)
        ctk.CTkLabel(mc, text="🖥  Chroot Manual", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(mc,
                     text=f"Monta a partição com bind de /dev /proc /sys em {CHROOT}",
                     font=F_SM, text_color=T["muted"]).pack(anchor="w", padx=20)
        br = ctk.CTkFrame(mc, fg_color="transparent")
        br.pack(fill="x", padx=20, pady=(8, 16))
        ctk.CTkButton(br, text="▶  Montar", height=36, width=140,
                      fg_color=T["accent"], text_color="#000",
                      hover_color=T["accent2"], font=F_BODY, corner_radius=8,
                      command=lambda: threading.Thread(
                          target=self._do_mount, daemon=True).start()
                      ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(br, text="■  Desmontar", height=36, width=130,
                      fg_color=T["border"], text_color=T["text"],
                      hover_color=T["card_hov"], font=F_BODY, corner_radius=8,
                      command=lambda: threading.Thread(
                          target=self._do_umount, daemon=True).start()
                      ).pack(side="left")

        # log
        self._rec_log = LogBox(sf)
        self._rec_log.pack(fill="x", padx=32, pady=(4, 28))

        self._refresh_parts()

    def _refresh_parts(self):
        parts = HW.linux_parts()
        entries = [f"{p['device']}  ({p['fstype']}  {p['size']})" for p in parts]
        if not entries: entries = ["(nenhuma partição Linux detectada)"]
        self._part_menu.configure(values=entries)
        self._part_var.set(entries[0])

    def _do_grub(self, disk):
        log = self._rec_log.log
        dev = self._part_var.get().split()[0]
        if not dev.startswith("/dev/"): log("[!] Partição inválida."); return
        log(f"Montando {dev}…")
        if not mount_chroot(dev, log): log("[!] Falha na montagem."); return
        log(f"Reinstalando GRUB em {disk}…")
        ok = repair_grub(disk, log)
        umount_chroot(log)
        log("[OK] GRUB reparado!" if ok else "[!] Falha no GRUB.")

    def _do_pw(self, user, pw):
        log = self._rec_log.log
        if not user or not pw: log("[!] Usuário/senha vazios."); return
        dev = self._part_var.get().split()[0]
        if not mount_chroot(dev, log): log("[!] Falha na montagem."); return
        ok = reset_password(user, pw, log)
        umount_chroot(log)
        log(f"[OK] Senha de '{user}' alterada." if ok else "[!] Falha.")

    def _do_mount(self):
        dev = self._part_var.get().split()[0]
        if not dev.startswith("/dev/"):
            self._rec_log.log("[!] Partição inválida."); return
        ok = mount_chroot(dev, self._rec_log.log)
        if ok:
            self._rec_log.log(f"[OK] Chroot pronto em {CHROOT}")
            self._rec_log.log(f"     sudo chroot {CHROOT} /bin/bash")

    def _do_umount(self):
        umount_chroot(self._rec_log.log)
        self._rec_log.log("[OK] Desmontado.")

    # ── Logs ──────────────────────────────────────────────

    def _logs_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "Logs", "Saída do sistema")

        for title, cmd in [
            ("dmesg  (últimas 30 linhas)", "dmesg | tail -30 2>/dev/null"),
            ("journalctl  (-n 30)",        "journalctl -n 30 --no-pager 2>/dev/null"),
        ]:
            ctk.CTkLabel(sf, text=title, font=F_HEAD,
                         text_color=T["text"]).pack(anchor="w", padx=32, pady=(16, 4))
            tb = ctk.CTkTextbox(sf, height=220, font=F_MONO,
                                fg_color=T["mono_bg"], text_color=T["mono_fg"],
                                corner_radius=10)
            tb.pack(fill="x", padx=32, pady=(0, 8))
            ok, out = CMD.run(cmd)
            tb.insert("end", out if ok else "(permissão negada ou comando indisponível)")
            tb.configure(state="disabled")

        ctk.CTkFrame(sf, fg_color="transparent", height=20).pack()


# ══════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════

def main():
    print(f"""
  ☕  CoffeeCat v{VERSION}  — Linux Rescue Toolkit
  ─────────────────────────────────────────────
""")
    missing = [t for t in ("lsblk", "smartctl", "grub-install", "dd", "wget", "pv")
               if not CMD.run(f"which {t}")[0]]
    if missing:
        print(f"  [!] Ferramentas opcionais ausentes: {', '.join(missing)}")
        print("      sudo apt install smartmontools grub2-common pv wget\n")
    if not CMD.is_root():
        print("  ⚠  Não está rodando como root.")
        print("     Funções completas: sudo python3 coffeecat.py\n")

    app = CoffeeCat()
    app.mainloop()


if __name__ == "__main__":
    main()
