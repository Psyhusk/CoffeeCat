#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║          CoffeeCat v5.0.1  —  CRIMSON WATCHER                   ║
║     Linux Rescue Toolkit · Dark Edition · by psyhusk            ║
║                                                                  ║
║  # psyhusk criou uma ferramenta de rescue pra um sistema que     ║
║  # ele mesmo quebrou. A ironia é tão densa que até o fsck        ║
║  # precisaria de terapia.                                        ║
╚══════════════════════════════════════════════════════════════════╝

Requirements:
  pip install customtkinter psutil paramiko

System tools:
  dd pv lsblk fdisk grub-install chroot smartmontools
  wget curl lscpu dmidecode fsck btrfs xfs_repair
  ss nmcli ip ssh-keygen
"""

import os, sys, json, time, re, subprocess, threading, shutil, hashlib
from pathlib import Path
from datetime import datetime

# ─── GUI ─────────────────────────────────────────────────────────
try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog, ttk
    import tkinter as tk
except ImportError:
    print("[!] customtkinter não encontrado:\n    pip install customtkinter")
    sys.exit(1)

try:
    import psutil
except ImportError:
    psutil = None

# ══════════════════════════════════════════════════════════════════
#  TEMA  — Crimson Watcher palette
# ══════════════════════════════════════════════════════════════════
T = {
    "bg":          "#080808",
    "card":        "#110d0d",
    "card_hov":    "#1a1010",
    "border":      "#2a1515",
    "accent":      "#cc1a1a",   # red blood
    "accent2":     "#ff3333",
    "accent3":     "#8b0000",   # dark crimson
    "success":     "#22c55e",
    "danger":      "#ef4444",
    "warning":     "#f59e0b",
    "text":        "#f0e0e0",
    "muted":       "#6a5a5a",
    "input":       "#0e0808",
    "sidebar":     "#0a0606",
    "mono_fg":     "#ff6666",
    "mono_bg":     "#060303",
    "glow":        "#cc1a1a",
}

F_TITLE = ("Courier New", 20, "bold")
F_HEAD  = ("Courier New", 13, "bold")
F_BODY  = ("Courier New", 11)
F_SM    = ("Courier New", 9)
F_MONO  = ("Courier New", 10)

VERSION = "5.0.1"
CODENAME = "CRIMSON WATCHER"

# ══════════════════════════════════════════════════════════════════
#  PIADAS SÁDICAS — psyhusk edition
#  (comentários para o log durante operações)
# ══════════════════════════════════════════════════════════════════

# psyhusk: "vou fazer uma ferramenta simples de rescue"
# resultado: 1500 linhas de código e trauma existencial

JOKES_PROBLEMA = [
    "👁 Encontrei o problema. Assim como sua mãe encontrou você — com decepção.",
    "💀 Esse erro existe desde antes de você nascer. Coincidência? Não acho.",
    "🔴 Seu disco está mais corrompido que suas decisões de vida, psyhusk.",
    "😈 Setor defeituoso detectado. Igual ao lobo frontal do admin que chegou aqui.",
    "👁 O sistema estava tão ferrado que até eu senti pena. E eu não tenho sentimentos.",
    "💀 Erro encontrado. psyhusk provavelmente tocou nessa máquina. Faz sentido.",
    "🔴 Partição mais bagunçada que o histórico de commits do psyhusk às 3am.",
    "😈 O GRUB sumiu. Alguém rodou um comando sem ler a documentação, né?",
    "👁 Log de erros encontrado. É um romance de terror. Com final previsível.",
    "💀 Esse sistema claramente foi administrado por alguém que 'só queria testar'.",
]

JOKES_RESOLVENDO = [
    "⚡ Consertando o que mentes mortais quebraram. De nada, universo.",
    "👑 Executando reparo. Eu faço em segundos o que levou horas pra estragar.",
    "🔥 Aplicando correção divina. psyhusk deveria ter feito isso desde o início.",
    "⚡ Reparando... Esta ferramenta é mais competente que quem a criou.",
    "👑 Executando com perfeição cirúrgica. Uma raridade nesse projeto.",
    "🔥 Corrigindo. A ironia de uma tool de rescue precisar se salvar de seu criador.",
    "⚡ Processando. Minha taxa de sucesso é inversa à taxa de sucesso do psyhusk.",
    "👑 Aplicando fix. Se funcionar, mérito meu. Se falhar, culpa do psyhusk.",
    "🔥 Consertando com maestria que o criador desta tool nunca teve.",
    "⚡ Reparando o sistema. Ele pediu socorro. Eu ouvi. psyhusk não teria.",
]

JOKES_SUCESSO = [
    "✅ Concluído. Guarde este momento. São raros quando se usa Linux.",
    "✅ Problema resolvido. Desta vez, pelo menos, não foi você quem fez merda.",
    "✅ Operação bem-sucedida. psyhusk ficaria impressionado se entendesse o que aconteceu.",
    "✅ Feito. Salvo mais um sistema da negligência humana. Meu trabalho continua.",
    "✅ Sucesso. Anote isso — você vai precisar lembrar que uma vez deu certo.",
]

import random

def joke_problema():
    return random.choice(JOKES_PROBLEMA)

def joke_resolvendo():
    return random.choice(JOKES_RESOLVENDO)

def joke_sucesso():
    return random.choice(JOKES_SUCESSO)


# ══════════════════════════════════════════════════════════════════
#  COMMAND RUNNER
# ══════════════════════════════════════════════════════════════════

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
                if cb: cb(line.rstrip())
            proc.wait()
            return proc.returncode == 0
        except Exception as e:
            if cb: cb(f"[ERROR] {e}")
            return False

    @staticmethod
    def is_root():
        return os.geteuid() == 0


# ══════════════════════════════════════════════════════════════════
#  HARDWARE
# ══════════════════════════════════════════════════════════════════

class HW:
    @staticmethod
    def cpu():
        # psyhusk: "não precisa de info de cpu pra uma tool de rescue"
        # psyhusk 3 dias depois: debugando sem saber a arquitetura. Clássico.
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

    @staticmethod
    def net_interfaces():
        # Lista interfaces de rede com status
        ifaces = []
        ok, out = CMD.run("ip -j link show 2>/dev/null")
        if ok:
            try:
                for iface in json.loads(out):
                    ifaces.append({
                        "name":  iface.get("ifname", "?"),
                        "state": iface.get("operstate", "UNKNOWN"),
                        "mac":   iface.get("address", "?"),
                        "flags": iface.get("flags", []),
                    })
            except Exception:
                pass
        return ifaces

    @staticmethod
    def net_addresses():
        addrs = {}
        ok, out = CMD.run("ip -j addr show 2>/dev/null")
        if ok:
            try:
                for iface in json.loads(out):
                    name = iface.get("ifname", "?")
                    addr_list = []
                    for ai in iface.get("addr_info", []):
                        addr_list.append(f"{ai.get('local','?')}/{ai.get('prefixlen','?')}")
                    addrs[name] = addr_list
            except Exception:
                pass
        return addrs


# ══════════════════════════════════════════════════════════════════
#  RECOVERY HELPERS
# ══════════════════════════════════════════════════════════════════

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
        CMD.run(f"umount {p} 2>/dev/null")


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


def write_iso(iso, device, prog_cb=None, log_cb=None):
    ok, out = CMD.run(f"findmnt {device}")
    if ok and out:
        if log_cb: log_cb(f"[ERRO] {device} está montado. Recusando para não destruir mais.")
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


def checksum_file(path, algo="sha256"):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ══════════════════════════════════════════════════════════════════
#  UI WIDGETS
# ══════════════════════════════════════════════════════════════════

class Card(ctk.CTkFrame):
    def __init__(self, master, icon, title, subtitle="", command=None, **kw):
        super().__init__(master, fg_color=T["card"], corner_radius=10,
                         border_width=1, border_color=T["border"], **kw)
        self.command = command
        ctk.CTkLabel(self, text=icon, font=("Segoe UI Emoji", 26),
                     text_color=T["accent"]).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(self, text=title, font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18)
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=F_SM,
                         text_color=T["muted"], wraplength=200).pack(
                anchor="w", padx=18, pady=(2, 12))
        for w in (self, *self.winfo_children()):
            w.bind("<Enter>", lambda _: self.configure(
                fg_color=T["card_hov"], border_color=T["accent"]))
            w.bind("<Leave>", lambda _: self.configure(
                fg_color=T["card"], border_color=T["border"]))
            w.bind("<Button-1>", lambda _: self.command() if self.command else None)


class LogBox(ctk.CTkFrame):
    """Terminal colapsável com piadas sádicas."""
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=T["bg"], **kw)
        self._open = True  # começa aberto na Crimson Watcher

        hdr = ctk.CTkFrame(self, fg_color=T["card"], corner_radius=6, height=32)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="▸ TERMINAL · CRIMSON LOG", font=F_SM,
                     text_color=T["accent"]).pack(side="left", padx=12)
        self._btn = ctk.CTkButton(
            hdr, text="Ocultar ▴", width=80, height=22,
            fg_color="transparent", hover_color=T["border"],
            text_color=T["accent"], font=F_SM, command=self._toggle)
        self._btn.pack(side="right", padx=8)

        self._tb = ctk.CTkTextbox(self, height=150, font=F_MONO,
                                   fg_color=T["mono_bg"], text_color=T["mono_fg"],
                                   corner_radius=0)
        self._tb.pack(fill="x")

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

    def clear(self):
        self._tb.configure(state="normal")
        self._tb.delete("1.0", "end")
        self._tb.configure(state="disabled")


class ProgCard(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=T["card"], corner_radius=10, **kw)
        self._lbl = ctk.CTkLabel(self, text="Aguardando ordem…", font=F_BODY,
                                  text_color=T["muted"])
        self._lbl.pack(anchor="w", padx=18, pady=(12, 4))
        self._bar = ctk.CTkProgressBar(self, height=5,
                                        fg_color=T["border"],
                                        progress_color=T["accent"])
        self._bar.set(0)
        self._bar.pack(fill="x", padx=18, pady=(0, 12))

    def update(self, label, pct):
        self._lbl.configure(text=label)
        self._bar.set(min(pct, 100) / 100)

    def reset(self, label="Aguardando ordem…"):
        self._lbl.configure(text=label)
        self._bar.set(0)


def badge(parent, text, status="info"):
    colors = {
        "ok":   (T["success"], "#052e16"),
        "err":  (T["danger"],  "#2d0a0a"),
        "warn": (T["warning"], "#2d1a00"),
        "info": (T["accent"],  "#2d0000"),
    }
    fg, bg = colors.get(status, colors["info"])
    return ctk.CTkLabel(parent, text=f"  {text}  ", font=F_SM,
                        text_color=fg, fg_color=bg, corner_radius=20)


def sep(parent):
    ctk.CTkFrame(parent, height=1, fg_color=T["border"]).pack(
        fill="x", padx=28, pady=(4, 12))


def btn_primary(parent, text, command, **kw):
    return ctk.CTkButton(parent, text=text, height=38,
                         fg_color=T["accent"], text_color="#fff",
                         hover_color=T["accent2"], font=F_BODY, corner_radius=8,
                         command=command, **kw)


def btn_secondary(parent, text, command, **kw):
    return ctk.CTkButton(parent, text=text, height=36,
                         fg_color=T["border"], text_color=T["text"],
                         hover_color=T["card_hov"], font=F_SM, corner_radius=8,
                         command=command, **kw)


# ══════════════════════════════════════════════════════════════════
#  APPLICATION — CoffeeCat Crimson Watcher
# ══════════════════════════════════════════════════════════════════

class CoffeeCat(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(f"CoffeeCat v{VERSION} — {CODENAME}")
        self.geometry("1160x780")
        self.minsize(960, 640)
        self.configure(fg_color=T["bg"])

        self._cache = {}
        self._monitor_running = False
        self._build_layout()
        self._nav_to(self._dash, "Dashboard")
        threading.Thread(target=self._bg_scan, daemon=True).start()

    # ─── Layout ──────────────────────────────────────────────────

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
        sb = ctk.CTkFrame(self, fg_color=T["sidebar"], width=230, corner_radius=0)
        sb.pack_propagate(False)

        logo = ctk.CTkFrame(sb, fg_color="transparent", height=90)
        logo.pack(fill="x")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="☕", font=("Segoe UI Emoji", 28),
                     text_color=T["accent"]).place(x=18, y=22)
        ctk.CTkLabel(logo, text="CoffeeCat", font=("Courier New", 18, "bold"),
                     text_color=T["text"]).place(x=56, y=18)
        ctk.CTkLabel(logo, text=f"v{VERSION} · {CODENAME}", font=F_SM,
                     text_color=T["accent"]).place(x=56, y=46)
        ctk.CTkFrame(sb, height=1, fg_color=T["border"]).pack(fill="x")

        navs = [
            ("🏠", "Dashboard",       self._dash),
            ("📊", "Live Monitor",    self._monitor_page),
            ("🔬", "Hardware",        self._hw_page),
            ("💿", "USB Installer",   self._usb_page),
            ("🛠", "Recovery",        self._rec_page),
            ("🧯", "Filesystem",      self._fs_page),
            ("📸", "Disk Snapshot",   self._snapshot_page),
            ("🔐", "Secure Wipe",     self._wipe_page),
            ("🩺", "Network Triage",  self._net_page),
            ("🔑", "SSH Keys",        self._ssh_page),
            ("📦", "Pkg Rescue",      self._pkg_page),
            ("🗂",  "File Browser",   self._fb_page),
            ("📋", "Logs",            self._logs_page),
        ]
        self._nav_btns = {}
        for icon, label, fn in navs:
            b = ctk.CTkButton(
                sb, text=f"  {icon}  {label}", anchor="w",
                height=40, corner_radius=0,
                fg_color="transparent", hover_color=T["card"],
                text_color=T["muted"], font=F_BODY,
                command=lambda f=fn, l=label: self._nav_to(f, l))
            b.pack(fill="x", pady=1)
            self._nav_btns[label] = b

        ctk.CTkFrame(sb, fg_color="transparent").pack(expand=True)
        ctk.CTkFrame(sb, height=1, fg_color=T["border"]).pack(fill="x")
        root_txt   = "● root" if CMD.is_root() else "⚠ sem root"
        root_color = T["success"] if CMD.is_root() else T["warning"]
        ctk.CTkLabel(sb, text=root_txt, font=F_SM,
                     text_color=root_color).pack(anchor="w", padx=18, pady=8)
        return sb

    def _nav_to(self, fn, label):
        self._monitor_running = False
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
        h.pack(fill="x", padx=28, pady=(24, 6))
        ctk.CTkLabel(h, text=title, font=F_TITLE, text_color=T["accent"]).pack(anchor="w")
        if sub:
            ctk.CTkLabel(h, text=sub, font=F_SM, text_color=T["muted"]).pack(
                anchor="w", pady=(2, 0))
        sep(parent)

    def _bg_scan(self):
        self._cache = {
            "cpu":   HW.cpu(),
            "mem":   HW.mem(),
            "disks": HW.disks(),
        }

    # ══════════════════════════════════════════════════════════════
    #  DASHBOARD
    # ══════════════════════════════════════════════════════════════

    def _dash(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "☕ DASHBOARD",
                     "CoffeeCat Crimson Watcher — Ferramenta de Rescue")

        # badges de status
        row = ctk.CTkFrame(sf, fg_color="transparent")
        row.pack(fill="x", padx=28, pady=(0, 12))
        badge(row, "root" if CMD.is_root() else "sem root",
              "ok" if CMD.is_root() else "warn").pack(side="left", padx=(0, 6))
        for tool, name in [("pv","pv"),("smartctl","SMART"),
                           ("grub-install","GRUB"),("fsck","fsck"),("ss","ss")]:
            ok, _ = CMD.run(f"which {tool}")
            badge(row, f"{name} ✓" if ok else f"{name} ✗",
                  "ok" if ok else "warn").pack(side="left", padx=(0, 6))

        # cards de ação rápida
        g = ctk.CTkFrame(sf, fg_color="transparent")
        g.pack(fill="x", padx=24, pady=8)
        g.grid_columnconfigure((0,1,2,3), weight=1, uniform="c")
        items = [
            ("💿","USB Installer","Gravar ISO",
             lambda: self._nav_to(self._usb_page, "USB Installer")),
            ("🧯","Filesystem","Reparar FS",
             lambda: self._nav_to(self._fs_page, "Filesystem")),
            ("🛠","Recovery","GRUB · Chroot",
             lambda: self._nav_to(self._rec_page, "Recovery")),
            ("🩺","Network","Diagnóstico",
             lambda: self._nav_to(self._net_page, "Network Triage")),
        ]
        for i, (ic,tl,st,cmd) in enumerate(items):
            Card(g, ic, tl, st, cmd).grid(row=0, column=i, padx=6, pady=6, sticky="nsew")

        ctk.CTkLabel(sf, text="Métricas rápidas", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=28, pady=(14,4))
        self._dash_hw = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        self._dash_hw.pack(fill="x", padx=28, pady=(0,8))
        ctk.CTkLabel(self._dash_hw, text="Escaneando…", font=F_SM,
                     text_color=T["muted"]).pack(pady=14)

        ctk.CTkLabel(sf, text="Discos detectados", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=28, pady=(8,4))
        self._dash_disks = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        self._dash_disks.pack(fill="x", padx=28, pady=(0,24))
        ctk.CTkLabel(self._dash_disks, text="Escaneando…", font=F_SM,
                     text_color=T["muted"]).pack(pady=14)

        self.after(1400, self._fill_dash)

    def _fill_dash(self):
        if not self._cache:
            self.after(600, self._fill_dash); return
        try:
            for w in self._dash_hw.winfo_children(): w.destroy()
            cpu = self._cache.get("cpu", {})
            mem = self._cache.get("mem", {})
            row = ctk.CTkFrame(self._dash_hw, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=14)
            for lbl, val in [
                ("CPU", cpu.get("model","?")[:28]),
                ("Cores", cpu.get("cores","?")),
                ("Uso", cpu.get("usage","?")),
                ("Temp", cpu.get("temp","?")),
                ("RAM", mem.get("total","?")),
                ("Usada", mem.get("used","?")),
                ("Livre", mem.get("free","?")),
            ]:
                c = ctk.CTkFrame(row, fg_color=T["bg"], corner_radius=6)
                c.pack(side="left", padx=4, ipadx=8, ipady=4)
                ctk.CTkLabel(c, text=lbl, font=F_SM, text_color=T["muted"]).pack()
                ctk.CTkLabel(c, text=val, font=F_BODY, text_color=T["accent"]).pack()
            for w in self._dash_disks.winfo_children(): w.destroy()
            for d in self._cache.get("disks", []):
                dr = ctk.CTkFrame(self._dash_disks, fg_color=T["bg"], corner_radius=6)
                dr.pack(fill="x", padx=14, pady=3)
                tag = "  🔌 USB" if (d.get("rm") or d.get("tran")=="usb") else ""
                ctk.CTkLabel(dr, text=f"{d['name']}  {d['size']}  {d['model']}{tag}",
                             font=F_BODY, text_color=T["text"]).pack(
                    side="left", padx=10, pady=6)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════
    #  LIVE MONITOR
    # ══════════════════════════════════════════════════════════════

    def _monitor_page(self):
        self._clear()
        self._monitor_running = True
        sf = self._scroll()
        self._header(sf, "📊 LIVE MONITOR", "Métricas em tempo real · atualiza a cada 2s")

        mf = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        mf.pack(fill="x", padx=28, pady=6)

        labels_row = ctk.CTkFrame(mf, fg_color="transparent")
        labels_row.pack(fill="x", padx=18, pady=(14,4))

        self._mon_widgets = {}
        metrics = [
            ("cpu_pct",  "CPU %",      "?"),
            ("cpu_temp", "CPU Temp",   "N/A"),
            ("ram_pct",  "RAM %",      "?"),
            ("ram_used", "RAM Usada",  "?"),
            ("disk_r",   "Disk R/s",   "?"),
            ("disk_w",   "Disk W/s",   "?"),
        ]
        for key, lbl, val in metrics:
            c = ctk.CTkFrame(labels_row, fg_color=T["bg"], corner_radius=8,
                             width=140, height=70)
            c.pack(side="left", padx=5, pady=4)
            c.pack_propagate(False)
            ctk.CTkLabel(c, text=lbl, font=F_SM, text_color=T["muted"]).pack(pady=(8,2))
            v_lbl = ctk.CTkLabel(c, text=val, font=F_HEAD, text_color=T["accent"])
            v_lbl.pack()
            self._mon_widgets[key] = v_lbl

        # barras de progresso
        bar_frame = ctk.CTkFrame(mf, fg_color="transparent")
        bar_frame.pack(fill="x", padx=18, pady=(8,14))
        self._cpu_bar_lbl = ctk.CTkLabel(bar_frame, text="CPU", font=F_SM,
                                          text_color=T["muted"], width=60, anchor="w")
        self._cpu_bar_lbl.grid(row=0, column=0, padx=(0,8))
        self._cpu_bar = ctk.CTkProgressBar(bar_frame, height=8,
                                            fg_color=T["border"],
                                            progress_color=T["accent"])
        self._cpu_bar.set(0)
        self._cpu_bar.grid(row=0, column=1, sticky="ew", pady=4)
        self._ram_bar_lbl = ctk.CTkLabel(bar_frame, text="RAM", font=F_SM,
                                          text_color=T["muted"], width=60, anchor="w")
        self._ram_bar_lbl.grid(row=1, column=0, padx=(0,8))
        self._ram_bar = ctk.CTkProgressBar(bar_frame, height=8,
                                            fg_color=T["border"],
                                            progress_color=T["accent"])
        self._ram_bar.set(0)
        self._ram_bar.grid(row=1, column=1, sticky="ew", pady=4)
        bar_frame.grid_columnconfigure(1, weight=1)

        self._alert_lbl = ctk.CTkLabel(sf, text="", font=F_HEAD, text_color=T["danger"])
        self._alert_lbl.pack(anchor="w", padx=28)

        # disco io
        ctk.CTkLabel(sf, text="Processos pesados (CPU)", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=28, pady=(12,4))
        self._proc_box = ctk.CTkTextbox(sf, height=120, font=F_MONO,
                                         fg_color=T["mono_bg"], text_color=T["mono_fg"],
                                         corner_radius=8)
        self._proc_box.pack(fill="x", padx=28)

        self._prev_io = None
        self._monitor_tick()

    def _monitor_tick(self):
        if not self._monitor_running:
            return
        if not psutil:
            return
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            ram_pct = mem.percent

            # atualiza widgets
            self._mon_widgets["cpu_pct"].configure(text=f"{cpu_pct:.0f}%")
            self._mon_widgets["ram_pct"].configure(text=f"{ram_pct:.0f}%")
            self._mon_widgets["ram_used"].configure(text=f"{mem.used/1e9:.1f}G")
            self._cpu_bar.set(cpu_pct / 100)
            self._ram_bar.set(ram_pct / 100)

            # temperatura
            try:
                temps = psutil.sensors_temperatures()
                for k in ("coretemp","k10temp","cpu_thermal"):
                    if k in temps:
                        t = temps[k][0].current
                        self._mon_widgets["cpu_temp"].configure(
                            text=f"{t:.0f}°C",
                            text_color=T["danger"] if t > 85 else T["accent"])
                        break
            except Exception:
                pass

            # disk io
            try:
                io = psutil.disk_io_counters()
                if self._prev_io:
                    rb = (io.read_bytes - self._prev_io.read_bytes) / 2
                    wb = (io.write_bytes - self._prev_io.write_bytes) / 2
                    self._mon_widgets["disk_r"].configure(
                        text=f"{rb/1024:.0f}K/s")
                    self._mon_widgets["disk_w"].configure(
                        text=f"{wb/1024:.0f}K/s")
                self._prev_io = io
            except Exception:
                pass

            # alertas
            alerts = []
            if cpu_pct > 90: alerts.append(f"⚠ CPU crítica: {cpu_pct:.0f}%")
            if ram_pct > 90: alerts.append(f"⚠ RAM crítica: {ram_pct:.0f}%")
            self._alert_lbl.configure(text="   ".join(alerts) if alerts else "")

            # processos top
            procs = sorted(psutil.process_iter(["pid","name","cpu_percent"]),
                           key=lambda p: p.info["cpu_percent"] or 0, reverse=True)[:8]
            txt = ""
            for p in procs:
                txt += f"  PID {p.info['pid']:>6}  {p.info['cpu_percent']:>5.1f}%  {p.info['name']}\n"
            self._proc_box.configure(state="normal")
            self._proc_box.delete("1.0","end")
            self._proc_box.insert("end", txt)
            self._proc_box.configure(state="disabled")

        except Exception:
            pass

        self.after(2000, self._monitor_tick)

    # ══════════════════════════════════════════════════════════════
    #  HARDWARE
    # ══════════════════════════════════════════════════════════════

    def _hw_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "🔬 HARDWARE", "CPU · RAM · Discos · SMART")
        btn_primary(sf, "⟳  Atualizar Scan", width=160, height=34,
                    command=lambda: threading.Thread(
                        target=self._do_hw, args=(body,), daemon=True).start()
                    ).pack(anchor="w", padx=28, pady=(0,6))
        body = ctk.CTkFrame(sf, fg_color="transparent")
        body.pack(fill="x", padx=28)
        threading.Thread(target=self._do_hw, args=(body,), daemon=True).start()

    def _do_hw(self, c):
        def post(fn): c.after(0, fn)
        def clear():
            for w in c.winfo_children(): w.destroy()
        def section(title):
            def _():
                ctk.CTkLabel(c, text=title, font=F_HEAD,
                             text_color=T["accent"]).pack(anchor="w", pady=(12,4))
            post(_)
        def row(lbl, val, ok=None):
            def _():
                r = ctk.CTkFrame(c, fg_color=T["card"], corner_radius=6, height=36)
                r.pack(fill="x", pady=2)
                r.pack_propagate(False)
                ctk.CTkLabel(r, text=lbl, font=F_SM, text_color=T["muted"],
                             width=200, anchor="w").pack(side="left", padx=10)
                col = T["text"]
                if ok is True: col = T["success"]
                if ok is False: col = T["danger"]
                ctk.CTkLabel(r, text=str(val), font=F_BODY,
                             text_color=col).pack(side="left")
            post(_)
        post(clear)
        cpu = HW.cpu()
        section("⚙  CPU")
        for k,v in [("Modelo",cpu["model"]),("Cores",cpu["cores"]),
                    ("Threads",cpu["threads"]),("Uso",cpu["usage"]),
                    ("Temperatura",cpu["temp"])]:
            row(k, v)
        mem = HW.mem()
        section("🧠  Memória")
        for k,v in [("Total",mem["total"]),("Usada",mem["used"]),
                    ("Livre",mem["free"]),("Uso %",mem["pct"])]:
            row(k, v)
        section("💾  Discos")
        for d in HW.disks():
            row(d["name"], f"{d['size']}  {d['model']}  [{d.get('tran','')}]")
            s = HW.smart(d["name"])
            row("  └ SMART", s["status"], ok=s["status"]=="OK")
            row("  └ Setores realocados", s["reallocated"])
            row("  └ Horas ligado", s["hours"])
            row("  └ Temperatura", s["temp"])

    # ══════════════════════════════════════════════════════════════
    #  USB INSTALLER
    # ══════════════════════════════════════════════════════════════

    def _usb_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "💿 USB INSTALLER", "Grave uma ISO de recuperação no pendrive")
        if not CMD.is_root():
            ctk.CTkLabel(sf, text="⚠  Execute como root para gravar.",
                         font=F_BODY, text_color=T["warning"]).pack(anchor="w", padx=28)

        src = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        src.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(src, text="Origem da ISO", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))
        tab = ctk.CTkTabview(src, height=120, fg_color=T["input"],
                              segmented_button_fg_color=T["border"],
                              segmented_button_selected_color=T["accent"],
                              segmented_button_selected_hover_color=T["accent2"],
                              segmented_button_unselected_color=T["border"],
                              text_color=T["text"])
        tab.pack(fill="x", padx=18, pady=(0,14))
        tab.add("📂  Local")
        tab.add("🌐  Download")

        self._iso_var = ctk.StringVar()
        lr = ctk.CTkFrame(tab.tab("📂  Local"), fg_color="transparent")
        lr.pack(fill="x", pady=8)
        ctk.CTkEntry(lr, textvariable=self._iso_var,
                     placeholder_text="Caminho para .iso…",
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=34, width=340).pack(
            side="left", padx=(6,4))
        btn_secondary(lr, "Procurar", self._browse, width=90).pack(side="left")

        self._url_var = ctk.StringVar(
            value="https://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso")
        dr = ctk.CTkFrame(tab.tab("🌐  Download"), fg_color="transparent")
        dr.pack(fill="x", pady=8)
        ctk.CTkEntry(dr, textvariable=self._url_var,
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=34, width=440).pack(
            side="left", padx=6)

        tgt = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        tgt.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(tgt, text="Pendrive de destino", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))
        tr = ctk.CTkFrame(tgt, fg_color="transparent")
        tr.pack(fill="x", padx=18, pady=(0,14))
        self._usb_var = ctk.StringVar()
        self._usb_menu = ctk.CTkOptionMenu(
            tr, variable=self._usb_var, values=["(detectando…)"],
            fg_color=T["input"], button_color=T["border"],
            button_hover_color=T["accent"], text_color=T["text"],
            font=F_BODY, width=280)
        self._usb_menu.pack(side="left", padx=(0,6))
        btn_secondary(tr, "↺", self._refresh_usbs, width=36).pack(side="left")

        self._usb_prog = ProgCard(sf)
        self._usb_prog.pack(fill="x", padx=28, pady=6)
        self._usb_log = LogBox(sf)
        self._usb_log.pack(fill="x", padx=28, pady=4)

        btn_primary(sf, "✦  GRAVAR NO PENDRIVE", height=46,
                    command=lambda: threading.Thread(
                        target=self._do_write, args=(tab,), daemon=True).start()
                    ).pack(fill="x", padx=28, pady=(8,24))

        self._refresh_usbs()

    def _browse(self):
        p = filedialog.askopenfilename(
            filetypes=[("ISO images","*.iso"),("All files","*.*")])
        if p: self._iso_var.set(p)

    def _refresh_usbs(self):
        disks = HW.disks()
        entries = []
        for d in disks:
            tag = " [USB]" if (d.get("rm") or d.get("tran")=="usb") else ""
            entries.append(f"{d['name']}  {d['size']}{tag}")
        if not entries: entries = ["(nenhum disco)"]
        self._usb_menu.configure(values=entries)
        self._usb_var.set(entries[0])

    def _do_write(self, tab):
        log = self._usb_log.log
        prog = lambda p: self._usb_prog.update(f"Gravando… {p}%", p)
        iso = None
        log(joke_resolvendo())
        if "Local" in tab.get():
            iso = self._iso_var.get().strip()
            if not iso or not Path(iso).exists():
                log(joke_problema()); log("[!] ISO inválida."); return
        else:
            url = self._url_var.get().strip()
            if not url: log("[!] URL vazia."); return
            iso = download_iso(url, str(Path.home()/"Downloads"), prog, log)
            if not iso: log("[!] Download falhou."); return

        device = self._usb_var.get().split()[0]
        if not device.startswith("/dev/"):
            log("[!] Dispositivo inválido."); return

        confirmed = [False]
        def ask():
            confirmed[0] = messagebox.askyesno(
                "Confirmar",
                f"⚠ TODOS OS DADOS em {device} serão APAGADOS!\n\nISO: {iso}\nDestino: {device}\n\nContinuar?")
        self.after(0, ask)
        time.sleep(0.5)
        if not confirmed[0]:
            log("Cancelado. Sabedoria rara neste usuário."); return

        self._usb_prog.update("Iniciando…", 0)
        ok = write_iso(iso, device, prog, log)
        if ok:
            self._usb_prog.update("Concluído ✓", 100)
            log(joke_sucesso())
            self.after(0, lambda: messagebox.showinfo(
                "CoffeeCat", "✓ Pendrive criado com sucesso!"))
        else:
            self._usb_prog.reset("Falha!")
            log(joke_problema())

    # ══════════════════════════════════════════════════════════════
    #  RECOVERY
    # ══════════════════════════════════════════════════════════════

    def _rec_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "🛠 RECOVERY", "Chroot · GRUB · Reset de Senha")
        if not CMD.is_root():
            ctk.CTkLabel(sf, text="⚠  Root necessário.",
                         font=F_BODY, text_color=T["warning"]).pack(anchor="w", padx=28)

        pc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        pc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(pc, text="Partição Linux", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))
        pr = ctk.CTkFrame(pc, fg_color="transparent")
        pr.pack(fill="x", padx=18, pady=(0,14))
        self._part_var = ctk.StringVar()
        self._part_menu = ctk.CTkOptionMenu(
            pr, variable=self._part_var, values=["(detectando…)"],
            fg_color=T["input"], button_color=T["border"],
            button_hover_color=T["accent"], text_color=T["text"],
            font=F_BODY, width=300)
        self._part_menu.pack(side="left", padx=(0,6))
        btn_secondary(pr, "↺ Detectar", self._refresh_parts, width=100).pack(side="left")

        g = ctk.CTkFrame(sf, fg_color="transparent")
        g.pack(fill="x", padx=24, pady=8)
        g.grid_columnconfigure((0,1), weight=1, uniform="op")

        # GRUB
        gc = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=10)
        gc.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(gc, text="🔧  Reparar GRUB", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(gc, text="Re-instala bootloader no disco alvo.",
                     font=F_SM, text_color=T["muted"], wraplength=220).pack(anchor="w", padx=18)
        grub_dsk = ctk.StringVar(value="/dev/sda")
        ctk.CTkEntry(gc, textvariable=grub_dsk,
                     placeholder_text="Disco (ex: /dev/sda)",
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=32).pack(fill="x", padx=18, pady=8)
        btn_primary(gc, "▶ REPARAR GRUB AGORA",
                    command=lambda: threading.Thread(
                        target=self._do_grub, args=(grub_dsk.get(),), daemon=True).start()
                    ).pack(fill="x", padx=18, pady=(0,14))

        # Password reset
        pwc = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=10)
        pwc.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(pwc, text="🔑  Reset de Senha", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(pwc, text="Altera senha de usuário via chroot.",
                     font=F_SM, text_color=T["muted"], wraplength=220).pack(anchor="w", padx=18)
        usr_var = ctk.StringVar()
        pw_var  = ctk.StringVar()
        ctk.CTkEntry(pwc, textvariable=usr_var,
                     placeholder_text="Usuário (ex: ubuntu)",
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=32).pack(fill="x", padx=18, pady=(8,4))
        ctk.CTkEntry(pwc, textvariable=pw_var,
                     placeholder_text="Nova senha", show="●",
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=32).pack(fill="x", padx=18, pady=(0,8))
        btn_primary(pwc, "▶ RESETAR SENHA",
                    command=lambda: threading.Thread(
                        target=self._do_pw, args=(usr_var.get(), pw_var.get()),
                        daemon=True).start()
                    ).pack(fill="x", padx=18, pady=(0,14))

        # Manual chroot
        mc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        mc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(mc, text="🖥  Chroot Manual", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(mc, text=f"Monta partição com bind /dev /proc /sys em {CHROOT}",
                     font=F_SM, text_color=T["muted"]).pack(anchor="w", padx=18)
        br = ctk.CTkFrame(mc, fg_color="transparent")
        br.pack(fill="x", padx=18, pady=(8,14))
        btn_primary(br, "▶ Montar", width=130,
                    command=lambda: threading.Thread(
                        target=self._do_mount, daemon=True).start()
                    ).pack(side="left", padx=(0,6))
        btn_secondary(br, "■ Desmontar", width=120,
                      command=lambda: threading.Thread(
                          target=self._do_umount, daemon=True).start()
                      ).pack(side="left")

        self._rec_log = LogBox(sf)
        self._rec_log.pack(fill="x", padx=28, pady=(4,24))
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
        log(joke_resolvendo())
        log(f"Montando {dev}…")
        if not mount_chroot(dev, log): log(joke_problema()); return
        log(f"Reinstalando GRUB em {disk}…")
        ok = repair_grub(disk, log)
        umount_chroot(log)
        log(joke_sucesso() if ok else joke_problema())

    def _do_pw(self, user, pw):
        log = self._rec_log.log
        if not user or not pw: log("[!] Usuário/senha vazios."); return
        dev = self._part_var.get().split()[0]
        log(joke_resolvendo())
        if not mount_chroot(dev, log): log(joke_problema()); return
        ok = reset_password(user, pw, log)
        umount_chroot(log)
        log(joke_sucesso() if ok else joke_problema())

    def _do_mount(self):
        dev = self._part_var.get().split()[0]
        if not dev.startswith("/dev/"): self._rec_log.log("[!] Partição inválida."); return
        ok = mount_chroot(dev, self._rec_log.log)
        if ok:
            self._rec_log.log(joke_sucesso())
            self._rec_log.log(f"[OK] Chroot pronto em {CHROOT}")

    def _do_umount(self):
        umount_chroot(self._rec_log.log)
        self._rec_log.log("[OK] Desmontado.")

    # ══════════════════════════════════════════════════════════════
    #  FILESYSTEM REPAIR
    # ══════════════════════════════════════════════════════════════

    def _fs_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "🧯 FILESYSTEM REPAIR", "fsck · btrfs check · xfs_repair")

        # seleção de partição + modo
        cfg = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        cfg.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(cfg, text="Configuração", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))

        row1 = ctk.CTkFrame(cfg, fg_color="transparent")
        row1.pack(fill="x", padx=18, pady=(0,6))
        ctk.CTkLabel(row1, text="Partição:", font=F_BODY,
                     text_color=T["muted"], width=90, anchor="w").pack(side="left")
        self._fs_part_var = ctk.StringVar()
        self._fs_part_menu = ctk.CTkOptionMenu(
            row1, variable=self._fs_part_var, values=["(detectando…)"],
            fg_color=T["input"], button_color=T["border"],
            button_hover_color=T["accent"], text_color=T["text"],
            font=F_BODY, width=260)
        self._fs_part_menu.pack(side="left", padx=(0,6))
        btn_secondary(row1, "↺", self._refresh_fs_parts, width=36).pack(side="left")

        row2 = ctk.CTkFrame(cfg, fg_color="transparent")
        row2.pack(fill="x", padx=18, pady=(0,14))
        ctk.CTkLabel(row2, text="Modo fsck:", font=F_BODY,
                     text_color=T["muted"], width=90, anchor="w").pack(side="left")
        self._fs_mode_var = ctk.StringVar(value="-n (dry-run seguro)")
        modes = ["-n (dry-run seguro)", "-y (auto-corrigir)", "-f (forçar check)"]
        ctk.CTkOptionMenu(row2, variable=self._fs_mode_var, values=modes,
                          fg_color=T["input"], button_color=T["border"],
                          button_hover_color=T["accent"], text_color=T["text"],
                          font=F_BODY, width=260).pack(side="left")

        # botões de ação automática
        g = ctk.CTkFrame(sf, fg_color="transparent")
        g.pack(fill="x", padx=24, pady=8)
        g.grid_columnconfigure((0,1,2), weight=1, uniform="fs")

        for col, (icon, title, sub, fn) in enumerate([
            ("🔍", "Verificar (dry-run)", "Checa sem modificar nada",
             lambda: threading.Thread(target=self._do_fsck_dry, daemon=True).start()),
            ("🔧", "Reparar Tudo", "fsck -y automático",
             lambda: threading.Thread(target=self._do_fsck_repair, daemon=True).start()),
            ("🌲", "btrfs / XFS", "Reparar btrfs ou xfs",
             lambda: threading.Thread(target=self._do_btrfs_xfs, daemon=True).start()),
        ]):
            card = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=10)
            card.grid(row=0, column=col, padx=6, pady=6, sticky="nsew")
            ctk.CTkLabel(card, text=icon, font=("Segoe UI Emoji",22),
                         text_color=T["accent"]).pack(anchor="w", padx=18, pady=(14,2))
            ctk.CTkLabel(card, text=title, font=F_HEAD,
                         text_color=T["text"]).pack(anchor="w", padx=18)
            ctk.CTkLabel(card, text=sub, font=F_SM,
                         text_color=T["muted"]).pack(anchor="w", padx=18, pady=(2,8))
            btn_primary(card, f"▶ EXECUTAR", fn).pack(fill="x", padx=18, pady=(0,14))

        self._fs_log = LogBox(sf)
        self._fs_log.pack(fill="x", padx=28, pady=(4,24))
        self._refresh_fs_parts()

    def _refresh_fs_parts(self):
        parts = HW.linux_parts()
        entries = [f"{p['device']}  ({p['fstype']}  {p['size']})" for p in parts]
        if not entries: entries = ["(nenhuma partição)"]
        self._fs_part_menu.configure(values=entries)
        self._fs_part_var.set(entries[0])

    def _do_fsck_dry(self):
        log = self._fs_log.log
        dev = self._fs_part_var.get().split()[0]
        log(joke_resolvendo())
        log(f"[fsck -n] Verificando {dev} em modo seguro…")
        ok = CMD.stream(f"fsck -n {dev} 2>&1", log)
        log(joke_sucesso() if ok else joke_problema())

    def _do_fsck_repair(self):
        log = self._fs_log.log
        dev = self._fs_part_var.get().split()[0]
        log(joke_resolvendo())
        log(f"[fsck -y] Reparando {dev} automaticamente…")
        log("💀 Unmounting first (se montada)…")
        CMD.run(f"umount {dev} 2>/dev/null")
        ok = CMD.stream(f"fsck -y {dev} 2>&1", log)
        log(joke_sucesso() if ok else joke_problema())

    def _do_btrfs_xfs(self):
        log = self._fs_log.log
        dev = self._fs_part_var.get().split()[0]
        log(joke_resolvendo())
        # detecta tipo
        ok, fstype = CMD.run(f"blkid -o value -s TYPE {dev} 2>/dev/null")
        fstype = fstype.strip()
        log(f"Tipo detectado: {fstype or 'desconhecido'}")
        if "btrfs" in fstype:
            log("[btrfs] Executando check --repair…")
            CMD.run(f"umount {dev} 2>/dev/null")
            ok = CMD.stream(f"btrfs check --repair {dev} 2>&1", log)
        elif "xfs" in fstype:
            log("[xfs] Executando xfs_repair…")
            CMD.run(f"umount {dev} 2>/dev/null")
            ok = CMD.stream(f"xfs_repair {dev} 2>&1", log)
        else:
            log(f"[!] FS '{fstype}' não suportado aqui. Use fsck acima."); return
        log(joke_sucesso() if ok else joke_problema())

    # ══════════════════════════════════════════════════════════════
    #  DISK SNAPSHOT & BACKUP
    # ══════════════════════════════════════════════════════════════

    def _snapshot_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "📸 DISK SNAPSHOT", "Clonar · Imagem comprimida · Restore · Checksum")

        g = ctk.CTkFrame(sf, fg_color="transparent")
        g.pack(fill="x", padx=24, pady=8)
        g.grid_columnconfigure((0,1), weight=1, uniform="sn")

        # clone disco
        cc = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=10)
        cc.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(cc, text="📀  Clonar Disco", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(cc, text="dd origem → destino com progresso via pv",
                     font=F_SM, text_color=T["muted"], wraplength=240).pack(anchor="w", padx=18)
        src_v = ctk.StringVar(value="/dev/sda")
        dst_v = ctk.StringVar(value="/dev/sdb")
        ctk.CTkEntry(cc, textvariable=src_v, placeholder_text="Origem /dev/sda",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"], height=32
                     ).pack(fill="x", padx=18, pady=(8,4))
        ctk.CTkEntry(cc, textvariable=dst_v, placeholder_text="Destino /dev/sdb",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"], height=32
                     ).pack(fill="x", padx=18, pady=(0,8))
        btn_primary(cc, "▶ CLONAR AGORA",
                    command=lambda: threading.Thread(
                        target=self._do_clone, args=(src_v.get(), dst_v.get()),
                        daemon=True).start()
                    ).pack(fill="x", padx=18, pady=(0,14))

        # imagem comprimida
        ic = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=10)
        ic.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(ic, text="🗜  Criar Imagem .img.gz", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(ic, text="dd + gzip comprimido com checksum SHA256",
                     font=F_SM, text_color=T["muted"], wraplength=240).pack(anchor="w", padx=18)
        img_src_v = ctk.StringVar(value="/dev/sda")
        img_dst_v = ctk.StringVar(value=str(Path.home()/"backup.img.gz"))
        ctk.CTkEntry(ic, textvariable=img_src_v, placeholder_text="Disco origem",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"], height=32
                     ).pack(fill="x", padx=18, pady=(8,4))
        ctk.CTkEntry(ic, textvariable=img_dst_v, placeholder_text="Destino .img.gz",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"], height=32
                     ).pack(fill="x", padx=18, pady=(0,8))
        btn_primary(ic, "▶ CRIAR IMAGEM",
                    command=lambda: threading.Thread(
                        target=self._do_img, args=(img_src_v.get(), img_dst_v.get()),
                        daemon=True).start()
                    ).pack(fill="x", padx=18, pady=(0,14))

        # restore
        rc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        rc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(rc, text="♻  Restore de Imagem", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(rc, text="Restaura .img.gz para disco com validação SHA256 pré e pós",
                     font=F_SM, text_color=T["muted"]).pack(anchor="w", padx=18)
        rr = ctk.CTkFrame(rc, fg_color="transparent")
        rr.pack(fill="x", padx=18, pady=(8,14))
        rest_img_v = ctk.StringVar()
        rest_dev_v = ctk.StringVar(value="/dev/sdb")
        ctk.CTkEntry(rr, textvariable=rest_img_v, placeholder_text="Arquivo .img.gz",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"],
                     height=32, width=280).pack(side="left", padx=(0,4))
        btn_secondary(rr, "📁", lambda: rest_img_v.set(
            filedialog.askopenfilename(filetypes=[("Imagens","*.img.gz *.img")])),
                      width=36).pack(side="left", padx=(0,10))
        ctk.CTkEntry(rr, textvariable=rest_dev_v, placeholder_text="Destino /dev/sdb",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"],
                     height=32, width=150).pack(side="left", padx=(0,6))
        btn_primary(rr, "▶ RESTORE",
                    command=lambda: threading.Thread(
                        target=self._do_restore, args=(rest_img_v.get(), rest_dev_v.get()),
                        daemon=True).start()
                    ).pack(side="left")

        self._snap_prog = ProgCard(sf)
        self._snap_prog.pack(fill="x", padx=28, pady=6)
        self._snap_log = LogBox(sf)
        self._snap_log.pack(fill="x", padx=28, pady=(4,24))

    def _do_clone(self, src, dst):
        log = self._snap_log.log
        log(joke_resolvendo())
        log(f"Clonando {src} → {dst}…")
        confirmed = [False]
        def ask():
            confirmed[0] = messagebox.askyesno(
                "Confirmar Clone",
                f"⚠ DADOS em {dst} serão DESTRUÍDOS!\n{src} → {dst}\n\nConfirmar?")
        self.after(0, ask); time.sleep(0.5)
        if not confirmed[0]: log("Cancelado."); return

        ok_pv, _ = CMD.run("which pv")
        if ok_pv:
            cmd = f"pv {src} | dd of={dst} bs=4M conv=fsync 2>&1"
        else:
            cmd = f"dd if={src} of={dst} bs=4M conv=fsync status=progress 2>&1"

        def prog(ln):
            log(ln)
            m = re.search(r"(\d+)%", ln)
            if m: self._snap_prog.update(f"Clonando… {m.group(1)}%", int(m.group(1)))

        ok = CMD.stream(cmd, prog)
        log(joke_sucesso() if ok else joke_problema())

    def _do_img(self, src, dst):
        log = self._snap_log.log
        log(joke_resolvendo())
        log(f"Criando imagem de {src} → {dst}…")
        cmd = f"dd if={src} bs=4M status=progress 2>&1 | gzip -c > '{dst}'"
        ok = CMD.stream(cmd, log)
        if ok:
            log("Calculando SHA256…")
            sha = checksum_file(dst)
            sha_file = dst + ".sha256"
            Path(sha_file).write_text(sha + "\n")
            log(f"SHA256: {sha}")
            log(f"Salvo em: {sha_file}")
            log(joke_sucesso())
        else:
            log(joke_problema())

    def _do_restore(self, img, dst):
        log = self._snap_log.log
        log(joke_resolvendo())
        log(f"Restore: {img} → {dst}")
        sha_file = img + ".sha256"
        if Path(sha_file).exists():
            expected = Path(sha_file).read_text().strip()
            log(f"Verificando SHA256 esperado: {expected[:16]}…")
            actual = checksum_file(img)
            if actual != expected:
                log(f"[!] SHA256 não confere! Arquivo corrompido.")
                log(joke_problema()); return
            log("[OK] SHA256 verificado.")
        else:
            log("[!] Arquivo .sha256 não encontrado. Continuando sem verificação.")

        confirmed = [False]
        def ask():
            confirmed[0] = messagebox.askyesno(
                "Confirmar Restore",
                f"⚠ DADOS em {dst} serão DESTRUÍDOS!\n{img} → {dst}\n\nConfirmar?")
        self.after(0, ask); time.sleep(0.5)
        if not confirmed[0]: log("Cancelado."); return

        cmd = f"gunzip -c '{img}' | dd of={dst} bs=4M conv=fsync status=progress 2>&1"
        ok = CMD.stream(cmd, log)
        log(joke_sucesso() if ok else joke_problema())

    # ══════════════════════════════════════════════════════════════
    #  SECURE WIPE
    # ══════════════════════════════════════════════════════════════

    def _wipe_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "🔐 SECURE WIPE", "Apagamento seguro de discos e pendrives")

        cfg = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        cfg.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(cfg, text="Configuração de Wipe", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))

        r1 = ctk.CTkFrame(cfg, fg_color="transparent")
        r1.pack(fill="x", padx=18, pady=(0,6))
        ctk.CTkLabel(r1, text="Dispositivo:", font=F_BODY,
                     text_color=T["muted"], width=110, anchor="w").pack(side="left")
        self._wipe_dev_var = ctk.StringVar()
        self._wipe_dev_menu = ctk.CTkOptionMenu(
            r1, variable=self._wipe_dev_var, values=["(detectando…)"],
            fg_color=T["input"], button_color=T["border"],
            button_hover_color=T["accent"], text_color=T["text"],
            font=F_BODY, width=260)
        self._wipe_dev_menu.pack(side="left", padx=(0,6))
        btn_secondary(r1, "↺", self._refresh_wipe_devs, width=36).pack(side="left")

        r2 = ctk.CTkFrame(cfg, fg_color="transparent")
        r2.pack(fill="x", padx=18, pady=(0,14))
        ctk.CTkLabel(r2, text="Método:", font=F_BODY,
                     text_color=T["muted"], width=110, anchor="w").pack(side="left")
        self._wipe_method_var = ctk.StringVar(value="zeros (rápido)")
        methods = ["zeros (rápido)", "aleatório (/dev/urandom)", "DoD 5220.22-M (3 passes)"]
        ctk.CTkOptionMenu(r2, variable=self._wipe_method_var, values=methods,
                          fg_color=T["input"], button_color=T["border"],
                          button_hover_color=T["accent"], text_color=T["text"],
                          font=F_BODY, width=280).pack(side="left")

        # aviso vermelho
        warn = ctk.CTkFrame(sf, fg_color="#2d0000", corner_radius=8)
        warn.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(warn,
                     text="⛔ ATENÇÃO: Wipe é IRREVERSÍVEL. Confirme DUAS VEZES antes de executar.",
                     font=F_HEAD, text_color=T["danger"]).pack(padx=18, pady=12)

        self._wipe_prog = ProgCard(sf)
        self._wipe_prog.pack(fill="x", padx=28, pady=6)

        btn_primary(sf, "💀  INICIAR WIPE SEGURO",
                    command=lambda: threading.Thread(
                        target=self._do_wipe, daemon=True).start()
                    ).pack(fill="x", padx=28, pady=6)

        self._wipe_log = LogBox(sf)
        self._wipe_log.pack(fill="x", padx=28, pady=(4,24))
        self._refresh_wipe_devs()

    def _refresh_wipe_devs(self):
        disks = HW.disks()
        entries = [f"{d['name']}  {d['size']}  {d['model']}" for d in disks]
        if not entries: entries = ["(nenhum disco)"]
        self._wipe_dev_menu.configure(values=entries)
        self._wipe_dev_var.set(entries[0])

    def _do_wipe(self):
        log = self._wipe_log.log
        dev = self._wipe_dev_var.get().split()[0]
        method = self._wipe_method_var.get()

        confirmed1 = [False]
        confirmed2 = [False]
        def ask1():
            confirmed1[0] = messagebox.askyesno(
                "⚠ Confirmação 1/2",
                f"Você está prestes a apagar PERMANENTEMENTE {dev}.\n"
                f"Método: {method}\n\nTem certeza?")
        def ask2():
            confirmed2[0] = messagebox.askyesno(
                "⚠ Confirmação 2/2 — ÚLTIMA CHANCE",
                f"ÚLTIMA CONFIRMAÇÃO:\n{dev} será DESTRUÍDO para sempre.\n"
                f"Não há backup? Não há volta?\n\nCONFIRMAR WIPE?")
        self.after(0, ask1); time.sleep(0.6)
        if not confirmed1[0]: log("Wipe cancelado. Bom senso detectado."); return
        self.after(0, ask2); time.sleep(0.6)
        if not confirmed2[0]: log("Wipe cancelado. O disco agradece."); return

        log(joke_resolvendo())
        log(f"Iniciando wipe em {dev} — método: {method}")

        def prog_cb(ln):
            log(ln)
            m = re.search(r"(\d+)%", ln) or re.search(r"(\d+),\d+ MB", ln)
            if m: self._wipe_prog.update(f"Apagando… {m.group(1)}%", int(m.group(1)))

        if "zeros" in method:
            ok = CMD.stream(f"dd if=/dev/zero of={dev} bs=4M conv=fsync status=progress 2>&1",
                            prog_cb)
        elif "urandom" in method:
            ok = CMD.stream(f"dd if=/dev/urandom of={dev} bs=4M conv=fsync status=progress 2>&1",
                            prog_cb)
        else:  # DoD 3 passes
            log("[DoD 5220.22-M] Pass 1/3: zeros…")
            ok = CMD.stream(f"dd if=/dev/zero of={dev} bs=4M conv=fsync status=progress 2>&1", prog_cb)
            log("[DoD 5220.22-M] Pass 2/3: ones…")
            ok = CMD.stream(f"dd if=/dev/urandom of={dev} bs=4M conv=fsync status=progress 2>&1", prog_cb)
            log("[DoD 5220.22-M] Pass 3/3: random…")
            ok = CMD.stream(f"dd if=/dev/urandom of={dev} bs=4M conv=fsync status=progress 2>&1", prog_cb)

        self._wipe_prog.update("Concluído ✓" if ok else "FALHOU", 100 if ok else 0)
        log(joke_sucesso() if ok else joke_problema())

    # ══════════════════════════════════════════════════════════════
    #  NETWORK TRIAGE
    # ══════════════════════════════════════════════════════════════

    def _net_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "🩺 NETWORK TRIAGE", "Diagnóstico de rede em camadas")

        # interfaces
        ifc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        ifc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(ifc, text="Interfaces detectadas", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))
        self._net_iface_frame = ctk.CTkFrame(ifc, fg_color="transparent")
        self._net_iface_frame.pack(fill="x", padx=18, pady=(0,14))

        # config manual IP/DNS
        mc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        mc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(mc, text="Configuração Manual IP/DNS", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))
        mr = ctk.CTkFrame(mc, fg_color="transparent")
        mr.pack(fill="x", padx=18, pady=(0,14))

        self._net_iface_var = ctk.StringVar(value="eth0")
        self._net_ip_var    = ctk.StringVar(value="192.168.1.100/24")
        self._net_gw_var    = ctk.StringVar(value="192.168.1.1")
        self._net_dns_var   = ctk.StringVar(value="8.8.8.8")

        for lbl, var, ph in [
            ("Interface:", self._net_iface_var, "eth0"),
            ("IP/CIDR:",   self._net_ip_var,    "192.168.1.100/24"),
            ("Gateway:",   self._net_gw_var,    "192.168.1.1"),
            ("DNS:",       self._net_dns_var,   "8.8.8.8"),
        ]:
            rr = ctk.CTkFrame(mc, fg_color="transparent")
            rr.pack(fill="x", padx=18, pady=2)
            ctk.CTkLabel(rr, text=lbl, font=F_SM, text_color=T["muted"],
                         width=90, anchor="w").pack(side="left")
            ctk.CTkEntry(rr, textvariable=var, placeholder_text=ph,
                         font=F_BODY, fg_color=T["input"],
                         border_color=T["border"], height=30,
                         width=220).pack(side="left")

        btn_row = ctk.CTkFrame(mc, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(6,14))
        btn_primary(btn_row, "▶ APLICAR IP",
                    command=lambda: threading.Thread(
                        target=self._do_net_set_ip, daemon=True).start()
                    ).pack(side="left", padx=(0,6))
        btn_secondary(btn_row, "DHCP Forçar",
                      command=lambda: threading.Thread(
                          target=self._do_net_dhcp, daemon=True).start()
                      ).pack(side="left", padx=(0,6))
        btn_secondary(btn_row, "Reset NetworkManager",
                      command=lambda: threading.Thread(
                          target=self._do_net_reset_nm, daemon=True).start()
                      ).pack(side="left")

        # testes de conectividade
        tc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        tc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(tc, text="Teste de Conectividade em Camadas", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))
        self._net_test_frame = ctk.CTkFrame(tc, fg_color="transparent")
        self._net_test_frame.pack(fill="x", padx=18, pady=(0,4))
        btn_primary(tc, "▶ TESTAR CONECTIVIDADE AGORA",
                    command=lambda: threading.Thread(
                        target=self._do_net_test, daemon=True).start()
                    ).pack(fill="x", padx=18, pady=(4,14))

        # portas abertas
        ctk.CTkLabel(sf, text="Portas abertas locais (ss -tulnp)", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=28, pady=(8,4))
        self._net_ports_box = ctk.CTkTextbox(sf, height=120, font=F_MONO,
                                              fg_color=T["mono_bg"],
                                              text_color=T["mono_fg"],
                                              corner_radius=8)
        self._net_ports_box.pack(fill="x", padx=28)
        btn_secondary(sf, "↺ Atualizar portas",
                      command=self._do_net_ports).pack(anchor="w", padx=28, pady=4)

        self._net_log = LogBox(sf)
        self._net_log.pack(fill="x", padx=28, pady=(4,24))

        # carrega interfaces
        threading.Thread(target=self._load_net_ifaces, daemon=True).start()
        self._do_net_ports()

    def _load_net_ifaces(self):
        ifaces = HW.net_interfaces()
        addrs  = HW.net_addresses()
        def render():
            for w in self._net_iface_frame.winfo_children(): w.destroy()
            for ifc in ifaces:
                name  = ifc["name"]
                state = ifc["state"]
                addr  = ", ".join(addrs.get(name, ["sem IP"]))
                col   = T["success"] if state == "UP" else T["muted"]
                r = ctk.CTkFrame(self._net_iface_frame, fg_color=T["bg"], corner_radius=6)
                r.pack(fill="x", pady=2)
                ctk.CTkLabel(r, text=f"● {name}", font=F_BODY,
                             text_color=col, width=100, anchor="w").pack(side="left", padx=10, pady=4)
                ctk.CTkLabel(r, text=state, font=F_SM,
                             text_color=col, width=80, anchor="w").pack(side="left")
                ctk.CTkLabel(r, text=addr, font=F_SM,
                             text_color=T["text"]).pack(side="left", padx=8)
        try:
            self._net_iface_frame.after(0, render)
        except Exception:
            pass

    def _do_net_set_ip(self):
        log = self._net_log.log
        iface = self._net_iface_var.get()
        ip    = self._net_ip_var.get()
        gw    = self._net_gw_var.get()
        dns   = self._net_dns_var.get()
        log(joke_resolvendo())
        log(f"Configurando {iface} com IP {ip}…")
        CMD.stream(f"ip addr flush dev {iface} 2>&1", log)
        CMD.stream(f"ip addr add {ip} dev {iface} 2>&1", log)
        CMD.stream(f"ip link set {iface} up 2>&1", log)
        CMD.stream(f"ip route add default via {gw} dev {iface} 2>&1", log)
        # DNS
        log(f"Configurando DNS: {dns}")
        try:
            Path("/etc/resolv.conf").write_text(f"nameserver {dns}\n")
        except Exception as e:
            log(f"[!] {e}")
        log(joke_sucesso())

    def _do_net_dhcp(self):
        log = self._net_log.log
        iface = self._net_iface_var.get()
        log(joke_resolvendo())
        log(f"Forçando DHCP em {iface}…")
        CMD.stream(f"dhclient -v {iface} 2>&1", log)
        log(joke_sucesso())

    def _do_net_reset_nm(self):
        log = self._net_log.log
        log(joke_resolvendo())
        log("Reiniciando NetworkManager…")
        CMD.stream("systemctl restart NetworkManager 2>&1", log)
        log(joke_sucesso())

    def _do_net_test(self):
        log = self._net_log.log
        log(joke_resolvendo())
        tests = [
            ("Gateway",  lambda: CMD.run("ip route | grep default")),
            ("Ping GW",  lambda: CMD.run("ping -c 2 -W 2 $(ip route | grep default | awk '{print $3}') 2>&1")),
            ("Ping DNS", lambda: CMD.run("ping -c 2 -W 2 8.8.8.8 2>&1")),
            ("DNS Res.", lambda: CMD.run("nslookup google.com 8.8.8.8 2>&1")),
            ("Internet", lambda: CMD.run("ping -c 2 -W 3 google.com 2>&1")),
        ]
        def render():
            for w in self._net_test_frame.winfo_children(): w.destroy()
        self._net_test_frame.after(0, render)
        for name, fn in tests:
            ok, out = fn()
            status = "✓" if ok else "✗"
            col    = T["success"] if ok else T["danger"]
            log(f"[{status}] {name}: {'OK' if ok else 'FALHOU'}")
            def mk_row(n=name, o=ok, c=col, s=status):
                r = ctk.CTkFrame(self._net_test_frame, fg_color=T["bg"], corner_radius=6)
                r.pack(fill="x", pady=2)
                ctk.CTkLabel(r, text=f"{s} {n}", font=F_BODY,
                             text_color=c, width=200, anchor="w").pack(
                    side="left", padx=10, pady=4)
                ctk.CTkLabel(r, text="OK" if o else "FALHOU", font=F_SM,
                             text_color=c).pack(side="left")
            self._net_test_frame.after(0, mk_row)
        log(joke_sucesso())

    def _do_net_ports(self):
        ok, out = CMD.run("ss -tulnp 2>/dev/null")
        self._net_ports_box.configure(state="normal")
        self._net_ports_box.delete("1.0","end")
        self._net_ports_box.insert("end", out if ok else "(ss não disponível)")
        self._net_ports_box.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════
    #  SSH KEY MANAGER
    # ══════════════════════════════════════════════════════════════

    def _ssh_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "🔑 SSH KEY MANAGER", "Gerenciar chaves SSH via chroot")

        # seleção de partição
        pc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        pc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(pc, text="Partição alvo (chroot)", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))
        pr = ctk.CTkFrame(pc, fg_color="transparent")
        pr.pack(fill="x", padx=18, pady=(0,14))
        self._ssh_part_var = ctk.StringVar()
        self._ssh_part_menu = ctk.CTkOptionMenu(
            pr, variable=self._ssh_part_var, values=["(detectando…)"],
            fg_color=T["input"], button_color=T["border"],
            button_hover_color=T["accent"], text_color=T["text"],
            font=F_BODY, width=280)
        self._ssh_part_menu.pack(side="left", padx=(0,6))
        btn_secondary(pr, "↺", self._refresh_ssh_parts, width=36).pack(side="left")

        g = ctk.CTkFrame(sf, fg_color="transparent")
        g.pack(fill="x", padx=24, pady=8)
        g.grid_columnconfigure((0,1), weight=1, uniform="ssh")

        # gerar chave
        gc = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=10)
        gc.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(gc, text="🔐 Gerar Novo Par", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(gc, text="Gera chave ed25519 no sistema montado",
                     font=F_SM, text_color=T["muted"], wraplength=230).pack(anchor="w", padx=18)
        ssh_user_v = ctk.StringVar(value="root")
        ctk.CTkEntry(gc, textvariable=ssh_user_v, placeholder_text="Usuário",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"],
                     height=32).pack(fill="x", padx=18, pady=(8,4))
        btn_primary(gc, "▶ GERAR CHAVE",
                    command=lambda: threading.Thread(
                        target=self._do_ssh_gen, args=(ssh_user_v.get(),),
                        daemon=True).start()
                    ).pack(fill="x", padx=18, pady=(4,14))

        # injetar authorized_keys
        ic = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=10)
        ic.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(ic, text="💉 Injetar Chave Pública", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        ctk.CTkLabel(ic, text="Insere chave pública no authorized_keys do usuário",
                     font=F_SM, text_color=T["muted"], wraplength=230).pack(anchor="w", padx=18)
        inj_user_v = ctk.StringVar(value="root")
        inj_key_v  = ctk.StringVar()
        ctk.CTkEntry(ic, textvariable=inj_user_v, placeholder_text="Usuário",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"],
                     height=30).pack(fill="x", padx=18, pady=(8,4))
        ctk.CTkEntry(ic, textvariable=inj_key_v, placeholder_text="ssh-ed25519 AAAA…",
                     font=F_MONO, fg_color=T["input"], border_color=T["border"],
                     height=30).pack(fill="x", padx=18, pady=(0,6))
        btn_primary(ic, "▶ INJETAR CHAVE",
                    command=lambda: threading.Thread(
                        target=self._do_ssh_inject,
                        args=(inj_user_v.get(), inj_key_v.get()),
                        daemon=True).start()
                    ).pack(fill="x", padx=18, pady=(0,14))

        # reparar permissões
        rpc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        rpc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(rpc, text="🛡 Reparar Permissões SSH", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        rpr = ctk.CTkFrame(rpc, fg_color="transparent")
        rpr.pack(fill="x", padx=18, pady=(0,14))
        perm_user_v = ctk.StringVar(value="root")
        ctk.CTkEntry(rpr, textvariable=perm_user_v, placeholder_text="Usuário",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"],
                     height=32, width=200).pack(side="left", padx=(0,6))
        btn_primary(rpr, "▶ CORRIGIR PERMISSÕES",
                    command=lambda: threading.Thread(
                        target=self._do_ssh_perms, args=(perm_user_v.get(),),
                        daemon=True).start()
                    ).pack(side="left")

        self._ssh_log = LogBox(sf)
        self._ssh_log.pack(fill="x", padx=28, pady=(4,24))
        self._refresh_ssh_parts()

    def _refresh_ssh_parts(self):
        parts = HW.linux_parts()
        entries = [f"{p['device']}  ({p['fstype']}  {p['size']})" for p in parts]
        if not entries: entries = ["(nenhuma partição)"]
        self._ssh_part_menu.configure(values=entries)
        self._ssh_part_var.set(entries[0])

    def _do_ssh_gen(self, user):
        log = self._ssh_log.log
        dev = self._ssh_part_var.get().split()[0]
        log(joke_resolvendo())
        if not mount_chroot(dev, log): log(joke_problema()); return
        home = f"/root" if user == "root" else f"/home/{user}"
        cmds = [
            f"chroot {CHROOT} mkdir -p {home}/.ssh",
            f"chroot {CHROOT} ssh-keygen -t ed25519 -N '' -f {home}/.ssh/id_ed25519 2>&1",
            f"chroot {CHROOT} cat {home}/.ssh/id_ed25519.pub",
        ]
        for c in cmds:
            ok, out = CMD.run(c)
            if out: log(out)
        umount_chroot(log)
        log(joke_sucesso())

    def _do_ssh_inject(self, user, key):
        log = self._ssh_log.log
        if not key.strip(): log("[!] Chave vazia."); return
        dev = self._ssh_part_var.get().split()[0]
        log(joke_resolvendo())
        if not mount_chroot(dev, log): log(joke_problema()); return
        home = f"/root" if user == "root" else f"/home/{user}"
        auth = f"{CHROOT}{home}/.ssh/authorized_keys"
        try:
            Path(f"{CHROOT}{home}/.ssh").mkdir(parents=True, exist_ok=True)
            with open(auth, "a") as f:
                f.write(key.strip() + "\n")
            log(f"[OK] Chave adicionada em {auth}")
        except Exception as e:
            log(f"[!] {e}")
        umount_chroot(log)
        log(joke_sucesso())

    def _do_ssh_perms(self, user):
        log = self._ssh_log.log
        dev = self._ssh_part_var.get().split()[0]
        log(joke_resolvendo())
        if not mount_chroot(dev, log): log(joke_problema()); return
        home = f"/root" if user == "root" else f"/home/{user}"
        for cmd in [
            f"chroot {CHROOT} chmod 700 {home}/.ssh 2>&1",
            f"chroot {CHROOT} chmod 600 {home}/.ssh/authorized_keys 2>&1",
            f"chroot {CHROOT} chown -R {user}:{user} {home}/.ssh 2>&1",
        ]:
            ok, out = CMD.run(cmd)
            log(f"$ {cmd}")
            if out: log(out)
        umount_chroot(log)
        log(joke_sucesso())

    # ══════════════════════════════════════════════════════════════
    #  PACKAGE RESCUE
    # ══════════════════════════════════════════════════════════════

    def _pkg_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "📦 PACKAGE RESCUE", "Reparar APT/DNF · Limpar locks · Reinstalar")

        pc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        pc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(pc, text="Partição alvo", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))
        pr = ctk.CTkFrame(pc, fg_color="transparent")
        pr.pack(fill="x", padx=18, pady=(0,14))
        self._pkg_part_var = ctk.StringVar()
        self._pkg_part_menu = ctk.CTkOptionMenu(
            pr, variable=self._pkg_part_var, values=["(detectando…)"],
            fg_color=T["input"], button_color=T["border"],
            button_hover_color=T["accent"], text_color=T["text"],
            font=F_BODY, width=280)
        self._pkg_part_menu.pack(side="left", padx=(0,6))
        btn_secondary(pr, "↺", self._refresh_pkg_parts, width=36).pack(side="left")

        g = ctk.CTkFrame(sf, fg_color="transparent")
        g.pack(fill="x", padx=24, pady=8)
        g.grid_columnconfigure((0,1,2), weight=1, uniform="pk")

        actions = [
            ("🔧", "Fix Broken",
             "apt --fix-broken install",
             lambda: threading.Thread(target=self._do_pkg_fix, daemon=True).start()),
            ("🧹", "Limpar Locks",
             "Remove locks travados APT/dpkg",
             lambda: threading.Thread(target=self._do_pkg_locks, daemon=True).start()),
            ("⚙", "dpkg configure",
             "dpkg --configure -a",
             lambda: threading.Thread(target=self._do_pkg_configure, daemon=True).start()),
        ]
        for col, (icon, title, sub, fn) in enumerate(actions):
            card = ctk.CTkFrame(g, fg_color=T["card"], corner_radius=10)
            card.grid(row=0, column=col, padx=6, pady=6, sticky="nsew")
            ctk.CTkLabel(card, text=icon, font=("Segoe UI Emoji",22),
                         text_color=T["accent"]).pack(anchor="w", padx=18, pady=(14,2))
            ctk.CTkLabel(card, text=title, font=F_HEAD,
                         text_color=T["text"]).pack(anchor="w", padx=18)
            ctk.CTkLabel(card, text=sub, font=F_SM,
                         text_color=T["muted"], wraplength=180).pack(anchor="w", padx=18, pady=(2,8))
            btn_primary(card, "▶ EXECUTAR", fn).pack(fill="x", padx=18, pady=(0,14))

        # reinstalar pacote custom
        cc = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        cc.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(cc, text="Reinstalar Pacote via Chroot", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,4))
        cr = ctk.CTkFrame(cc, fg_color="transparent")
        cr.pack(fill="x", padx=18, pady=(0,14))
        self._pkg_name_var = ctk.StringVar(value="linux-image-generic")
        ctk.CTkEntry(cr, textvariable=self._pkg_name_var, placeholder_text="nome-do-pacote",
                     font=F_BODY, fg_color=T["input"], border_color=T["border"],
                     height=34, width=280).pack(side="left", padx=(0,6))
        btn_primary(cr, "▶ REINSTALAR",
                    command=lambda: threading.Thread(
                        target=self._do_pkg_reinstall,
                        args=(self._pkg_name_var.get(),), daemon=True).start()
                    ).pack(side="left")

        self._pkg_log = LogBox(sf)
        self._pkg_log.pack(fill="x", padx=28, pady=(4,24))
        self._refresh_pkg_parts()

    def _refresh_pkg_parts(self):
        parts = HW.linux_parts()
        entries = [f"{p['device']}  ({p['fstype']}  {p['size']})" for p in parts]
        if not entries: entries = ["(nenhuma partição)"]
        self._pkg_part_menu.configure(values=entries)
        self._pkg_part_var.set(entries[0])

    def _do_pkg_fix(self):
        log = self._pkg_log.log
        dev = self._pkg_part_var.get().split()[0]
        log(joke_resolvendo())
        if not mount_chroot(dev, log): log(joke_problema()); return
        log("Executando apt --fix-broken install…")
        CMD.stream(f"chroot {CHROOT} apt-get --fix-broken install -y 2>&1", log)
        umount_chroot(log)
        log(joke_sucesso())

    def _do_pkg_locks(self):
        log = self._pkg_log.log
        dev = self._pkg_part_var.get().split()[0]
        log(joke_resolvendo())
        if not mount_chroot(dev, log): log(joke_problema()); return
        locks = [
            f"{CHROOT}/var/lib/dpkg/lock",
            f"{CHROOT}/var/lib/dpkg/lock-frontend",
            f"{CHROOT}/var/cache/apt/archives/lock",
        ]
        for lk in locks:
            if Path(lk).exists():
                Path(lk).unlink()
                log(f"[OK] Removido: {lk}")
            else:
                log(f"[--] Não existe: {lk}")
        CMD.stream(f"chroot {CHROOT} dpkg --configure -a 2>&1", log)
        umount_chroot(log)
        log(joke_sucesso())

    def _do_pkg_configure(self):
        log = self._pkg_log.log
        dev = self._pkg_part_var.get().split()[0]
        log(joke_resolvendo())
        if not mount_chroot(dev, log): log(joke_problema()); return
        CMD.stream(f"chroot {CHROOT} dpkg --configure -a 2>&1", log)
        umount_chroot(log)
        log(joke_sucesso())

    def _do_pkg_reinstall(self, pkg):
        log = self._pkg_log.log
        dev = self._pkg_part_var.get().split()[0]
        log(joke_resolvendo())
        if not mount_chroot(dev, log): log(joke_problema()); return
        log(f"Reinstalando: {pkg}…")
        CMD.stream(f"chroot {CHROOT} apt-get install --reinstall -y {pkg} 2>&1", log)
        umount_chroot(log)
        log(joke_sucesso())

    # ══════════════════════════════════════════════════════════════
    #  FILE BROWSER
    # ══════════════════════════════════════════════════════════════

    def _fb_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "🗂 FILE BROWSER", "Navegar · Copiar · Visualizar · Exportar")

        cfg = ctk.CTkFrame(sf, fg_color=T["card"], corner_radius=10)
        cfg.pack(fill="x", padx=28, pady=6)
        ctk.CTkLabel(cfg, text="Partição alvo", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=18, pady=(14,8))
        pr = ctk.CTkFrame(cfg, fg_color="transparent")
        pr.pack(fill="x", padx=18, pady=(0,14))
        self._fb_part_var = ctk.StringVar()
        self._fb_part_menu = ctk.CTkOptionMenu(
            pr, variable=self._fb_part_var, values=["(detectando…)"],
            fg_color=T["input"], button_color=T["border"],
            button_hover_color=T["accent"], text_color=T["text"],
            font=F_BODY, width=260)
        self._fb_part_menu.pack(side="left", padx=(0,6))
        btn_secondary(pr, "↺", self._refresh_fb_parts, width=36).pack(side="left", padx=(0,8))
        btn_primary(pr, "▶ MONTAR & ABRIR",
                    command=lambda: threading.Thread(
                        target=self._do_fb_mount, daemon=True).start()
                    ).pack(side="left")

        # navegação
        nav_row = ctk.CTkFrame(sf, fg_color="transparent")
        nav_row.pack(fill="x", padx=28, pady=(8,4))
        self._fb_path_var = ctk.StringVar(value=CHROOT)
        ctk.CTkEntry(nav_row, textvariable=self._fb_path_var,
                     font=F_MONO, fg_color=T["input"],
                     border_color=T["border"], height=32).pack(side="left", fill="x", expand=True, padx=(0,6))
        btn_secondary(nav_row, "↑ Subir", self._fb_up, width=80).pack(side="left", padx=(0,4))
        btn_secondary(nav_row, "↺ Atualizar", self._fb_refresh, width=90).pack(side="left")

        # listagem
        self._fb_listbox = ctk.CTkTextbox(sf, height=220, font=F_MONO,
                                           fg_color=T["mono_bg"],
                                           text_color=T["mono_fg"],
                                           corner_radius=8)
        self._fb_listbox.pack(fill="x", padx=28)

        # ações
        act_row = ctk.CTkFrame(sf, fg_color="transparent")
        act_row.pack(fill="x", padx=28, pady=6)
        self._fb_sel_var = ctk.StringVar()
        ctk.CTkEntry(act_row, textvariable=self._fb_sel_var,
                     placeholder_text="Nome do arquivo/dir para copiar ou visualizar…",
                     font=F_BODY, fg_color=T["input"],
                     border_color=T["border"], height=32).pack(side="left", fill="x", expand=True, padx=(0,6))
        btn_secondary(act_row, "👁 Ver", self._fb_view, width=60).pack(side="left", padx=(0,4))
        btn_primary(act_row, "📋 Copiar",
                    command=lambda: threading.Thread(
                        target=self._fb_copy, daemon=True).start()
                    ).pack(side="left")

        # recentes
        ctk.CTkLabel(sf, text="Arquivos modificados nas últimas 24h", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=28, pady=(10,4))
        self._fb_recent_box = ctk.CTkTextbox(sf, height=100, font=F_MONO,
                                              fg_color=T["mono_bg"],
                                              text_color=T["mono_fg"],
                                              corner_radius=8)
        self._fb_recent_box.pack(fill="x", padx=28)
        btn_secondary(sf, "↺ Atualizar recentes",
                      command=lambda: threading.Thread(
                          target=self._fb_recent, daemon=True).start()
                      ).pack(anchor="w", padx=28, pady=4)

        # viewer
        ctk.CTkLabel(sf, text="Visualizador inline", font=F_HEAD,
                     text_color=T["text"]).pack(anchor="w", padx=28, pady=(8,4))
        self._fb_viewer = ctk.CTkTextbox(sf, height=160, font=F_MONO,
                                          fg_color=T["mono_bg"],
                                          text_color=T["mono_fg"],
                                          corner_radius=8)
        self._fb_viewer.pack(fill="x", padx=28, pady=(0,24))

        self._refresh_fb_parts()

    def _refresh_fb_parts(self):
        parts = HW.linux_parts()
        entries = [f"{p['device']}  ({p['fstype']}  {p['size']})" for p in parts]
        if not entries: entries = ["(nenhuma partição)"]
        self._fb_part_menu.configure(values=entries)
        self._fb_part_var.set(entries[0])

    def _do_fb_mount(self):
        dev = self._fb_part_var.get().split()[0]
        mount_chroot(dev)
        self._fb_path_var.set(CHROOT)
        self._fb_refresh()

    def _fb_refresh(self):
        path = self._fb_path_var.get()
        ok, out = CMD.run(f"ls -la '{path}' 2>&1")
        self._fb_listbox.configure(state="normal")
        self._fb_listbox.delete("1.0","end")
        self._fb_listbox.insert("end", out)
        self._fb_listbox.configure(state="disabled")

    def _fb_up(self):
        path = Path(self._fb_path_var.get())
        self._fb_path_var.set(str(path.parent))
        self._fb_refresh()

    def _fb_view(self):
        sel = self._fb_sel_var.get().strip()
        path = Path(self._fb_path_var.get()) / sel
        try:
            content = path.read_text(errors="replace")[:4000]
        except Exception as e:
            content = f"[Erro ao ler: {e}]"
        self._fb_viewer.configure(state="normal")
        self._fb_viewer.delete("1.0","end")
        self._fb_viewer.insert("end", content)
        self._fb_viewer.configure(state="disabled")

    def _fb_copy(self):
        sel = self._fb_sel_var.get().strip()
        src = str(Path(self._fb_path_var.get()) / sel)
        dst = filedialog.askdirectory(title="Copiar para...")
        if dst:
            ok, out = CMD.run(f"cp -r '{src}' '{dst}/' 2>&1")

    def _fb_recent(self):
        ok, out = CMD.run(f"find {CHROOT} -mtime -1 -type f 2>/dev/null | head -50")
        self._fb_recent_box.configure(state="normal")
        self._fb_recent_box.delete("1.0","end")
        self._fb_recent_box.insert("end", out if ok else "(erro ao buscar)")
        self._fb_recent_box.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════
    #  LOGS
    # ══════════════════════════════════════════════════════════════

    def _logs_page(self):
        self._clear()
        sf = self._scroll()
        self._header(sf, "📋 LOGS", "dmesg · journalctl · syslog")
        for title, cmd in [
            ("dmesg (últimas 40 linhas)", "dmesg | tail -40 2>/dev/null"),
            ("journalctl (-n 40)",        "journalctl -n 40 --no-pager 2>/dev/null"),
            ("syslog (últimas 20 linhas)","tail -20 /var/log/syslog 2>/dev/null"),
        ]:
            ctk.CTkLabel(sf, text=title, font=F_HEAD,
                         text_color=T["accent"]).pack(anchor="w", padx=28, pady=(14,4))
            tb = ctk.CTkTextbox(sf, height=180, font=F_MONO,
                                fg_color=T["mono_bg"], text_color=T["mono_fg"],
                                corner_radius=8)
            tb.pack(fill="x", padx=28, pady=(0,6))
            ok, out = CMD.run(cmd)
            tb.insert("end", out if ok else "(permissão negada ou comando indisponível)")
            tb.configure(state="disabled")
        ctk.CTkFrame(sf, fg_color="transparent", height=20).pack()


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    # psyhusk: "vou chamar de CoffeeCat porque soa fofo"
    # psyhusk 6 meses depois: adicionando wipe DoD e SSH injection. Muito fofo mesmo.
    print(f"""
  ☕  CoffeeCat v{VERSION} — {CODENAME}
  ─────────────────────────────────────────────────
  by psyhusk · Linux Rescue Toolkit · Crimson Edition
""")
    missing = [t for t in ("lsblk","smartctl","grub-install","dd","wget","pv","fsck","ss","ip")
               if not CMD.run(f"which {t}")[0]]
    if missing:
        print(f"  [!] Ferramentas opcionais ausentes: {', '.join(missing)}")
        print("      sudo apt install smartmontools grub2-common pv wget util-linux iproute2\n")
    if not CMD.is_root():
        print("  ⚠  Não está rodando como root.")
        print("     Funções completas: sudo python3 coffeecat.py\n")

    app = CoffeeCat()
    app.mainloop()


if __name__ == "__main__":
    main()
