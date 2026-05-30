#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoffeeCat v5.0.1 — CRIMSON WATCHER — Script de Build (PyInstaller)
===================================================================
Compila o instalador e o toolkit em executável único.

Execute no mesmo diretório que 'coffeecat_installer.py' e 'coffeecat.py'.

Pré-requisitos:
  pip install pyinstaller customtkinter psutil Pillow

Uso:
  python build_coffeecat.py

Resultado:
  dist/CoffeeCat_v501_CrimsonWatcher          (Linux/macOS)
  dist/CoffeeCat_v501_CrimsonWatcher.exe      (Windows)

─────────────────────────────────────────────────────────────
# psyhusk fez um build script copiando a estrutura do SeerCat.
# Nem o próprio sistema de build escapou do ctrl+c, ctrl+v.
# A coragem é admirável. O resultado, menos.
─────────────────────────────────────────────────────────────
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

# ─── Configuração do build ────────────────────────────────
NOME_APP      = "CoffeeCat_v501_CrimsonWatcher"
SCRIPT_MAIN   = "coffeecat_installer.py"   # ponto de entrada = instalador
SCRIPT_TOOL   = "coffeecat.py"             # bundled junto
VERSION       = "5.0.1"
CODENAME      = "CRIMSON WATCHER"

# Ícone (coloque um .png ou .ico no diretório)
ICONE_PNG = "coffeecat_icon.png"

# Arquivos extras a incluir no bundle (o toolkit principal DEVE vir junto)
DATAS_EXTRAS = []
if os.path.exists(SCRIPT_TOOL):
    DATAS_EXTRAS.append((SCRIPT_TOOL, "."))
if os.path.exists(ICONE_PNG):
    pass  # tratado pela função converter_icone

def verificar_pyinstaller():
    """Verifica se PyInstaller está instalado, instala se não."""
    try:
        import PyInstaller
        print(f"[+] PyInstaller {PyInstaller.__version__} disponível.")
        return True
    except ImportError:
        print("[!] PyInstaller não encontrado. Instalando...")
        ret = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            capture_output=True, text=True
        )
        if ret.returncode == 0:
            print("[+] PyInstaller instalado com sucesso.")
            return True
        else:
            print(f"[-] Falha ao instalar PyInstaller:\n{ret.stderr}")
            return False

def converter_icone():
    """
    Converte ícone PNG para ICO (Windows) ou PNG (Linux/macOS).
    Se não existir ícone, gera um placeholder vermelho automaticamente.
    """
    import platform
    so = platform.system()

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("[!] Pillow não encontrado. Instalando para gerar ícone…")
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow"],
                       capture_output=True)
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            print("[!] Pillow indisponível — build sem ícone customizado.")
            return None

    # Gera ícone se não existir
    if not os.path.exists(ICONE_PNG):
        print("[*] Ícone não encontrado — gerando placeholder Crimson…")
        img = Image.new("RGBA", (256, 256), (8, 8, 8, 255))
        draw = ImageDraw.Draw(img)
        # círculo vermelho com ☕
        draw.ellipse([28, 28, 228, 228], outline=(204, 26, 26), width=6)
        draw.ellipse([60, 60, 196, 196], fill=(17, 13, 13))
        draw.text((88, 88), "☕", fill=(204, 26, 26))
        img.save(ICONE_PNG, format="PNG")
        print(f"[+] Ícone gerado: {ICONE_PNG}")

    try:
        img = Image.open(ICONE_PNG).convert("RGBA").resize((256, 256), Image.LANCZOS)
        if so == "Windows":
            ico_path = "coffeecat.ico"
            img.save(ico_path, format="ICO",
                     sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        else:
            ico_path = "coffeecat_build_icon.png"
            img.save(ico_path, format="PNG")
        print(f"[+] Ícone pronto: {ico_path}")
        return ico_path
    except Exception as e:
        print(f"[!] Erro ao processar ícone: {e}")
        return None

def verificar_scripts():
    """Garante que os arquivos principais existem."""
    ok = True
    for f in [SCRIPT_MAIN, SCRIPT_TOOL]:
        if os.path.exists(f):
            print(f"[+] Encontrado: {f}")
        else:
            print(f"[-] FALTANDO: {f}  ← coloque no mesmo diretório!")
            ok = False
    return ok

def build():
    """Executa o build via PyInstaller."""
    print()
    print("=" * 60)
    print(f"  CoffeeCat v{VERSION} — {CODENAME}")
    print("  Build Script")
    print("=" * 60)
    print()

    # psyhusk: "o build vai funcionar na primeira vez"
    # realidade: nunca funciona na primeira vez.

    if not verificar_pyinstaller():
        sys.exit(1)

    if not verificar_scripts():
        print()
        print("[-] Coloque coffeecat.py e coffeecat_installer.py no")
        print("    mesmo diretório que este script e tente novamente.")
        sys.exit(1)

    icone_path = converter_icone()

    # ── Monta comando PyInstaller ─────────────────────────
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",        # executável único
        "--windowed",       # sem console no Windows
        "--name", NOME_APP,
        "--clean",
        "--noconfirm",
    ]

    if icone_path and os.path.exists(icone_path):
        cmd += ["--icon", icone_path]

    # Inclui coffeecat.py dentro do bundle
    for src, dst in DATAS_EXTRAS:
        cmd += ["--add-data", f"{src}{os.pathsep}{dst}"]

    # Hidden imports
    hidden_imports = [
        # tkinter
        "tkinter",
        "tkinter.font",
        "tkinter.messagebox",
        "tkinter.filedialog",
        "tkinter.ttk",
        # customtkinter e deps
        "customtkinter",
        "customtkinter.windows",
        "customtkinter.windows.widgets",
        "customtkinter.windows.widgets.appearance_mode",
        "darkdetect",
        "packaging",
        "packaging.version",
        # psutil
        "psutil",
        "psutil._pslinux",
        "psutil._psposix",
        # stdlib extras
        "pathlib",
        "hashlib",
        "threading",
        "subprocess",
        "shutil",
        "json",
        "re",
        "math",
        "random",
        "datetime",
    ]
    for hi in hidden_imports:
        cmd += ["--hidden-import", hi]

    # Coleta módulos inteiros
    for mod in ["customtkinter", "psutil"]:
        cmd += ["--collect-submodules", mod]
        cmd += ["--collect-data", mod]

    # Script principal (instalador)
    cmd.append(SCRIPT_MAIN)

    print(f"\n[>] Iniciando build PyInstaller…")
    print(f"    Entry:  {SCRIPT_MAIN}")
    print(f"    Bundle: {SCRIPT_TOOL}")
    print(f"    Output: dist/{NOME_APP}")
    print()

    resultado = subprocess.run(cmd, text=True)

    if resultado.returncode == 0:
        print()
        print("=" * 60)
        print("  BUILD CONCLUÍDO COM SUCESSO!")
        print("=" * 60)

        import platform
        ext    = ".exe" if platform.system() == "Windows" else ""
        binario = Path("dist") / f"{NOME_APP}{ext}"

        if binario.exists():
            tamanho = binario.stat().st_size / (1024 * 1024)
            print(f"\n  Executável : {binario}")
            print(f"  Tamanho    : {tamanho:.1f} MB")
            print(f"  Plataforma : {platform.system()} {platform.machine()}")

        print()
        print("  Para instalar:")
        print(f"    ./{NOME_APP}        (Linux/macOS)")
        print(f"    .\\{NOME_APP}.exe   (Windows)")
        print()
        print("  Para distribuir, copie apenas o arquivo de dist/")
        print()

        # psyhusk vai distribuir um executável que só funciona
        # na máquina dele. Tradicional.

    else:
        print()
        print("[-] BUILD FALHOU.")
        print("    Verifique os erros acima.")
        print()
        print("    Dicas de debug:")
        print("      • pip install customtkinter psutil Pillow")
        print("      • Certifique-se de ter Python 3.8+")
        print("      • Em Linux, instale: sudo apt install python3-tk")
        sys.exit(1)

def limpar_artifacts():
    """Remove .spec e pastas temporárias do PyInstaller."""
    for item in [f"{NOME_APP}.spec", "build"]:
        p = Path(item)
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            print(f"[*] Removido: {item}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description=f"Build script — CoffeeCat v{VERSION} {CODENAME}")
    parser.add_argument("--clean-only", action="store_true",
                        help="Apenas limpa artifacts sem buildar")
    args = parser.parse_args()

    if args.clean_only:
        limpar_artifacts()
    else:
        build()
        # limpa spec e pasta build após sucesso
        limpar_artifacts()
