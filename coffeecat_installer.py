#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║   CoffeeCat v5.0.1 CRIMSON WATCHER — Installer          ║
║   Janela frameless · fundo transparente · red glow       ║
║   by psyhusk                                             ║
╚══════════════════════════════════════════════════════════╝
"""

import os, sys, subprocess, threading, shutil, time
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import font as tkfont
except ImportError:
    print("[!] tkinter não encontrado.")
    sys.exit(1)

# ── Paleta Crimson ────────────────────────────────────────
BG_COLOR    = "#080808"
GLOW_COLOR  = "#cc1a1a"
GLOW_DARK   = "#8b0000"
TEXT_COLOR  = "#f0e0e0"
MUTED_COLOR = "#6a5a5a"
MONO_COLOR  = "#ff6666"
SUCCESS     = "#22c55e"
DANGER      = "#ef4444"
CARD        = "#110d0d"

VERSION  = "5.0.1"
CODENAME = "CRIMSON WATCHER"

INSTALL_DIR  = Path.home() / ".local" / "share" / "coffeecat"
BIN_LINK     = Path.home() / ".local" / "bin" / "coffeecat"
DESKTOP_FILE = Path.home() / ".local" / "share" / "applications" / "coffeecat.desktop"
MAIN_SCRIPT  = "coffeecat.py"


# ══════════════════════════════════════════════════════════
#  GATO ASCII ART + PENTAGRAMA (arte em canvas)
# ══════════════════════════════════════════════════════════

CAT_ART = """
       ██████████████
     ██░░░░░░░░░░░░░░██
    █░░░░░░░░░░░░░░░░░░█
   █░░  ██░░░░░░░░██  ░░█
   █░░ █▓▓█░░░░░░█▓▓█ ░░█
   █░░░░░░░░░░░░░░░░░░░░█
   █░░░  ░▀▄░░░▄▀░  ░░░█
   █░░░░░░░▀███▀░░░░░░░█
    █░░░░░░░░░░░░░░░░░█
     ██░░░░░░░░░░░░░██
       ████████████████
"""

PENTAGRAM = """
          ★
        ╱   ╲
       ╱  ✦  ╲
      ╱─────────╲
     ╱  ╲     ╱  ╲
    ╱    ╲   ╱    ╲
   ╱──────╲ ╱──────╲
"""

# ══════════════════════════════════════════════════════════
#  STEPS DE INSTALAÇÃO
# ══════════════════════════════════════════════════════════

STEPS = [
    ("Verificando dependências Python",   20),
    ("Instalando customtkinter",          35),
    ("Instalando psutil",                 50),
    ("Copiando arquivos",                 65),
    ("Criando atalho de execução",        78),
    ("Criando entrada .desktop",          88),
    ("Verificando ferramentas do sistema",95),
    ("Instalação concluída",             100),
]


def run_cmd(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:
        return False, str(e)


def do_install(log_cb, prog_cb, done_cb):
    """Lógica real de instalação rodando em thread."""
    errors = []

    def step(msg, pct, fn=None):
        log_cb(f"[>>] {msg}")
        if fn:
            ok, out = fn()
            if not ok:
                log_cb(f"[!!] {out[:120] if out else 'Falhou'}")
                errors.append(msg)
            else:
                if out: log_cb(f"     {out[:80]}")
        prog_cb(pct, msg)
        time.sleep(0.3)

    # 1 - check python
    step("Verificando Python 3.8+", 15, lambda: (sys.version_info >= (3,8), sys.version))

    # 2 - customtkinter
    step("Instalando customtkinter", 30,
         lambda: run_cmd(f"{sys.executable} -m pip install customtkinter --quiet"))

    # 3 - psutil
    step("Instalando psutil", 45,
         lambda: run_cmd(f"{sys.executable} -m pip install psutil --quiet"))

    # 4 - copiar arquivos
    log_cb("[>>] Copiando arquivos para ~/.local/share/coffeecat …")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(__file__).parent / MAIN_SCRIPT
    if src.exists():
        shutil.copy2(src, INSTALL_DIR / MAIN_SCRIPT)
        log_cb(f"     Copiado: {src} → {INSTALL_DIR / MAIN_SCRIPT}")
    else:
        log_cb(f"[!!] {MAIN_SCRIPT} não encontrado no diretório atual.")
        errors.append("Arquivo principal não encontrado")
    prog_cb(65, "Arquivos copiados")
    time.sleep(0.3)

    # 5 - symlink
    log_cb("[>>] Criando atalho em ~/.local/bin/coffeecat …")
    BIN_LINK.parent.mkdir(parents=True, exist_ok=True)
    if BIN_LINK.exists() or BIN_LINK.is_symlink():
        BIN_LINK.unlink()
    launcher = BIN_LINK.parent / "coffeecat"
    launcher.write_text(
        f"#!/bin/bash\nexec {sys.executable} {INSTALL_DIR / MAIN_SCRIPT} \"$@\"\n"
    )
    launcher.chmod(0o755)
    log_cb(f"     Atalho criado: {BIN_LINK}")
    prog_cb(78, "Atalho criado")
    time.sleep(0.3)

    # 6 - .desktop
    log_cb("[>>] Criando entrada .desktop …")
    DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_FILE.write_text(f"""[Desktop Entry]
Name=CoffeeCat {VERSION}
Comment=Linux Rescue Toolkit · Crimson Watcher
Exec={sys.executable} {INSTALL_DIR / MAIN_SCRIPT}
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=System;Utility;
Keywords=rescue;linux;recovery;disk;
""")
    log_cb(f"     .desktop criado: {DESKTOP_FILE}")
    prog_cb(88, ".desktop criado")
    time.sleep(0.3)

    # 7 - ferramentas do sistema
    log_cb("[>>] Verificando ferramentas do sistema …")
    tools = ["lsblk","smartctl","grub-install","dd","wget","pv","fsck","ss","ip"]
    missing = [t for t in tools if not run_cmd(f"which {t}")[0]]
    if missing:
        log_cb(f"     [!] Ausentes: {', '.join(missing)}")
        log_cb("     Instale: sudo apt install smartmontools grub2-common pv wget iproute2")
    else:
        log_cb("     Todas as ferramentas detectadas.")
    prog_cb(95, "Verificação concluída")
    time.sleep(0.3)

    # done
    prog_cb(100, "Concluído")
    time.sleep(0.2)
    done_cb(errors)


# ══════════════════════════════════════════════════════════
#  JANELA PRINCIPAL — frameless + transparent + red glow
# ══════════════════════════════════════════════════════════

class CrimsonInstaller(tk.Tk):

    W = 780
    H = 580

    def __init__(self):
        super().__init__()

        # ── janela sem bordas ──
        self.overrideredirect(True)           # sem decoração do WM
        self.attributes("-topmost", False)
        self.configure(bg=BG_COLOR)

        # transparência (funciona no X11 com compositor ativo)
        try:
            self.attributes("-alpha", 0.96)
        except Exception:
            pass

        self._center()
        self.geometry(f"{self.W}x{self.H}")

        # drag da janela
        self._drag_x = 0
        self._drag_y = 0

        self._build()
        self._animate_glow()

    def _center(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - self.W) // 2
        y  = (sh - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

    # ── Construção da UI ──────────────────────────────────

    def _build(self):
        self._canvas = tk.Canvas(self, width=self.W, height=self.H,
                                  bg=BG_COLOR, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        # Borda com glow (desenhada no canvas)
        self._glow_rect = self._canvas.create_rectangle(
            2, 2, self.W-2, self.H-2,
            outline=GLOW_COLOR, width=2)
        self._glow_outer = self._canvas.create_rectangle(
            0, 0, self.W, self.H,
            outline=GLOW_DARK, width=1)

        # Drag handlers na barra de título
        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",       self._on_drag)

        self._draw_cat_art()
        self._draw_header()
        self._draw_content()

    def _draw_cat_art(self):
        """Desenha o gato com olhos vermelhos e pentagrama no canvas."""
        c = self._canvas

        # fundo do gato — painel lateral direito
        c.create_rectangle(520, 60, 760, 520, fill="#0a0404", outline=GLOW_DARK, width=1)

        # Desenha gato pixel por pixel (formas geométricas)
        # Cabeça
        c.create_oval(570, 80, 720, 210, fill="#111", outline=GLOW_COLOR, width=1)
        # Orelhas
        c.create_polygon(575, 120, 560, 75, 600, 100, fill="#1a0808", outline=GLOW_COLOR)
        c.create_polygon(715, 120, 730, 75, 690, 100, fill="#1a0808", outline=GLOW_COLOR)
        # Orelhas internas
        c.create_polygon(578, 115, 566, 83, 597, 103, fill=GLOW_DARK)
        c.create_polygon(712, 115, 724, 83, 693, 103, fill=GLOW_DARK)

        # OLHOS VERMELHOS — brilhantes
        # olho esquerdo
        c.create_oval(598, 125, 632, 155, fill="#330000", outline=GLOW_COLOR, width=2)
        c.create_oval(608, 132, 624, 148, fill=GLOW_COLOR)
        c.create_oval(612, 136, 618, 142, fill="#ff6666")  # reflexo
        # olho direito
        c.create_oval(658, 125, 692, 155, fill="#330000", outline=GLOW_COLOR, width=2)
        c.create_oval(668, 132, 684, 148, fill=GLOW_COLOR)
        c.create_oval(672, 136, 678, 142, fill="#ff6666")

        # pupila vertical
        c.create_oval(613, 128, 619, 152, fill="#000")
        c.create_oval(673, 128, 679, 152, fill="#000")

        # Nariz
        c.create_polygon(640, 165, 634, 172, 646, 172, fill=GLOW_DARK)
        # Boca
        c.create_arc(625, 168, 643, 182, start=180, extent=180,
                     outline=GLOW_COLOR, style="arc", width=1)
        c.create_arc(643, 168, 661, 182, start=180, extent=180,
                     outline=GLOW_COLOR, style="arc", width=1)

        # Bigodes
        for y_off in [-3, 0, 3]:
            c.create_line(560, 168+y_off, 620, 168+y_off,
                          fill=GLOW_DARK, width=1)
            c.create_line(670, 168+y_off, 730, 168+y_off,
                          fill=GLOW_DARK, width=1)

        # Corpo
        c.create_oval(575, 200, 715, 310, fill="#0d0505", outline=GLOW_COLOR, width=1)
        # Patas
        c.create_oval(578, 295, 618, 330, fill="#110808", outline=GLOW_DARK, width=1)
        c.create_oval(672, 295, 712, 330, fill="#110808", outline=GLOW_DARK, width=1)
        # Pata dianteira
        c.create_oval(590, 308, 622, 340, fill="#110808", outline=GLOW_DARK, width=1)
        c.create_oval(670, 308, 702, 340, fill="#110808", outline=GLOW_DARK, width=1)

        # Cauda
        c.create_arc(620, 270, 760, 360, start=0, extent=200,
                     outline=GLOW_COLOR, style="arc", width=2)

        # PENTAGRAMA abaixo do gato
        cx, cy, r = 645, 440, 55
        import math
        pts = []
        for i in range(5):
            angle = math.radians(-90 + i * 144)
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

        # círculo do pentagrama
        c.create_oval(cx-r-8, cy-r-8, cx+r+8, cy+r+8,
                      outline=GLOW_COLOR, width=1)

        # linhas do pentagrama
        order = [0, 2, 4, 1, 3, 0]
        for i in range(len(order)-1):
            c.create_line(pts[order[i]][0], pts[order[i]][1],
                          pts[order[i+1]][0], pts[order[i+1]][1],
                          fill=GLOW_COLOR, width=1)

        # estrela central
        c.create_text(cx, cy, text="✦", font=("Courier New", 14, "bold"),
                      fill=GLOW_COLOR)

        # texto "COFFEECAT" sobre a arte
        c.create_text(645, 510, text="COFFEECAT", font=("Courier New", 10, "bold"),
                      fill=GLOW_DARK)
        c.create_text(645, 523, text="CRIMSON WATCHER", font=("Courier New", 8),
                      fill=MUTED_COLOR)

    def _draw_header(self):
        c = self._canvas

        # barra de título
        c.create_rectangle(0, 0, 520, 50, fill="#0a0404", outline="")
        c.create_line(0, 50, 520, 50, fill=GLOW_DARK, width=1)

        # ícone + título
        c.create_text(20, 25, text="☕", font=("Segoe UI Emoji", 18),
                      fill=GLOW_COLOR, anchor="w")
        c.create_text(50, 16, text=f"CoffeeCat v{VERSION}", font=("Courier New", 14, "bold"),
                      fill=TEXT_COLOR, anchor="w")
        c.create_text(50, 34, text=CODENAME, font=("Courier New", 9),
                      fill=GLOW_COLOR, anchor="w")

        # botão fechar
        self._close_btn = c.create_text(500, 25, text="✕",
                                         font=("Courier New", 14, "bold"),
                                         fill=MUTED_COLOR)
        c.tag_bind(self._close_btn, "<Enter>",
                   lambda e: c.itemconfigure(self._close_btn, fill=GLOW_COLOR))
        c.tag_bind(self._close_btn, "<Leave>",
                   lambda e: c.itemconfigure(self._close_btn, fill=MUTED_COLOR))
        c.tag_bind(self._close_btn, "<Button-1>", lambda e: self.destroy())

    def _draw_content(self):
        """Área de instalação — lado esquerdo."""
        c = self._canvas

        # separador vertical
        c.create_line(520, 50, 520, self.H, fill=GLOW_DARK, width=1)

        # subtítulo
        c.create_text(20, 68, text="Linux Rescue Toolkit · Instalador",
                      font=("Courier New", 10), fill=MUTED_COLOR, anchor="w")
        c.create_line(0, 82, 520, 82, fill=GLOW_DARK, width=1)

        # barra de progresso (fundo)
        c.create_rectangle(20, 340, 495, 358, fill="#1a0808", outline=GLOW_DARK, width=1)
        self._prog_bar = c.create_rectangle(20, 340, 20, 358,
                                             fill=GLOW_COLOR, outline="")
        self._prog_pct_text = c.create_text(258, 349, text="0%",
                                             font=("Courier New", 9, "bold"),
                                             fill=TEXT_COLOR)

        # label status
        self._status_text = c.create_text(20, 370,
                                           text="Aguardando…",
                                           font=("Courier New", 10),
                                           fill=MUTED_COLOR, anchor="w")

        # log textbox (frame tk dentro do canvas)
        self._log_frame = tk.Frame(self, bg=BG_COLOR)
        self._log_frame.place(x=18, y=390, width=490, height=130)
        self._log_text = tk.Text(
            self._log_frame,
            bg="#060303", fg=MONO_COLOR,
            font=("Courier New", 9),
            relief="flat", bd=0,
            state="disabled",
            wrap="word",
            insertbackground=GLOW_COLOR,
        )
        sb = tk.Scrollbar(self._log_frame, orient="vertical",
                          command=self._log_text.yview,
                          bg=BG_COLOR, troughcolor=BG_COLOR,
                          activebackground=GLOW_COLOR)
        self._log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True)

        # borda do log
        c.create_rectangle(17, 388, 509, 522, outline=GLOW_DARK, width=1)

        # botões
        self._install_btn = tk.Button(
            self,
            text="▶  INSTALAR AGORA",
            font=("Courier New", 12, "bold"),
            bg=GLOW_COLOR, fg="#fff",
            activebackground=GLOW_DARK, activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2",
            command=self._start_install,
        )
        self._install_btn.place(x=18, y=532, width=240, height=36)

        self._launch_btn = tk.Button(
            self,
            text="🚀  LANÇAR COFFEECAT",
            font=("Courier New", 11, "bold"),
            bg="#1a1a1a", fg=MUTED_COLOR,
            activebackground=CARD, activeforeground=TEXT_COLOR,
            relief="flat", bd=0, cursor="arrow",
            state="disabled",
            command=self._launch,
        )
        self._launch_btn.place(x=270, width=240, y=532, height=36)

        # info de destino
        c.create_text(20, 92, text="Destino de instalação:", font=("Courier New", 9),
                      fill=MUTED_COLOR, anchor="w")
        c.create_text(20, 106, text=str(INSTALL_DIR),
                      font=("Courier New", 9, "bold"), fill=TEXT_COLOR, anchor="w")

        # lista de componentes
        c.create_text(20, 128, text="Componentes incluídos:",
                      font=("Courier New", 10, "bold"), fill=TEXT_COLOR, anchor="w")
        components = [
            "📊 Live Monitor — CPU/RAM tempo real",
            "🧯 Filesystem Repair — fsck/btrfs/xfs",
            "📸 Disk Snapshot — clone + imagem .img.gz",
            "🔐 Secure Wipe — DoD 5220.22-M",
            "🩺 Network Triage — diagnóstico em camadas",
            "🔑 SSH Key Manager — via chroot",
            "📦 Package Rescue — APT/dpkg repair",
            "🗂  File Browser — navegar sistema montado",
        ]
        for i, comp in enumerate(components):
            c.create_text(24, 148 + i*22, text=comp,
                          font=("Courier New", 9), fill=MUTED_COLOR, anchor="w")
            c.create_text(18, 150 + i*22, text="›",
                          font=("Courier New", 9), fill=GLOW_COLOR, anchor="w")

        c.create_line(0, 326, 520, 326, fill=GLOW_DARK, width=1)
        c.create_text(20, 335, text="Progresso:", font=("Courier New", 9),
                      fill=MUTED_COLOR, anchor="w")

    # ── Animação de glow ─────────────────────────────────

    def _animate_glow(self):
        """Pisca suavemente a borda vermelha."""
        colors = [
            "#cc1a1a","#d42020","#dc2626","#d42020","#cc1a1a",
            "#b81515","#a01010","#b81515","#cc1a1a",
        ]
        self._glow_idx = 0

        def tick():
            if not self.winfo_exists():
                return
            col = colors[self._glow_idx % len(colors)]
            self._canvas.itemconfigure(self._glow_rect, outline=col)
            self._glow_idx += 1
            self.after(120, tick)

        tick()

    # ── Drag ─────────────────────────────────────────────

    def _on_press(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x  = self.winfo_x() + dx
        y  = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    # ── Instalação ───────────────────────────────────────

    def _log(self, msg):
        def _do():
            self._log_text.configure(state="normal")
            self._log_text.insert("end", msg + "\n")
            self._log_text.see("end")
            self._log_text.configure(state="disabled")
        try:
            self._log_text.after(0, _do)
        except Exception:
            pass

    def _prog(self, pct, msg=""):
        def _do():
            w = int((pct / 100) * 475)
            self._canvas.coords(self._prog_bar, 20, 340, 20+w, 358)
            self._canvas.itemconfigure(self._prog_pct_text, text=f"{pct}%")
            if msg:
                self._canvas.itemconfigure(self._status_text, text=msg)
        try:
            self._canvas.after(0, _do)
        except Exception:
            pass

    def _done(self, errors):
        def _do():
            if errors:
                self._canvas.itemconfigure(
                    self._status_text,
                    text=f"⚠ Concluído com avisos: {len(errors)} erros")
                self._canvas.itemconfigure(self._status_text,
                                            fill=GLOW_COLOR)
            else:
                self._canvas.itemconfigure(self._status_text,
                                            text="✓ Instalação concluída com sucesso!")
                self._canvas.itemconfigure(self._status_text, fill=SUCCESS)
            self._install_btn.configure(state="disabled", bg="#1a0808")
            self._launch_btn.configure(
                state="normal", bg=GLOW_COLOR, fg="#fff",
                activebackground=GLOW_DARK, cursor="hand2")
        try:
            self._canvas.after(0, _do)
        except Exception:
            pass

    def _start_install(self):
        self._install_btn.configure(state="disabled", text="Instalando…")
        self._log("☕ CoffeeCat Crimson Watcher — Iniciando instalação…")
        self._log("─" * 55)
        threading.Thread(
            target=do_install,
            args=(self._log, self._prog, self._done),
            daemon=True
        ).start()

    def _launch(self):
        target = INSTALL_DIR / MAIN_SCRIPT
        if target.exists():
            subprocess.Popen([sys.executable, str(target)])
            self.after(800, self.destroy)
        else:
            self._log(f"[!] Arquivo não encontrado: {target}")


# ══════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = CrimsonInstaller()
    app.mainloop()
