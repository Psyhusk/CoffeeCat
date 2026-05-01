# ☕ CoffeeCat — Linux Rescue Toolkit

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-yellow.svg)](https://opensource.org/licenses/AGPL-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![UI: CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-black.svg)](https://github.com/TomSchimansky/CustomTkinter)

**CoffeeCat** é um canivete suíço para manutenção de sistemas Linux, focado em fornecer uma experiência moderna e intuitiva para tarefas críticas de recuperação. Inspirado no design de aplicativos de Neobanking (como o C6 Bank), ele elimina a complexidade do terminal para reparos emergenciais.

---

## ✨ Funcionalidades

* **💿 USB Installer:** Gravação de ISOs via `dd` com feedback visual em tempo real (utilizando `pv`).
* **🛠 Recovery Automático:** Montagem de ambiente `chroot` com um clique (bind de `/dev`, `/proc`, `/sys`).
* **🔧 Reparo de Boot:** Reinstalação e atualização do GRUB diretamente no disco alvo.
* **🔑 Reset de Senha:** Alteração de senhas de usuários do sistema Linux montado via chroot.
* **🔬 Hardware Health:** Diagnóstico SMART de discos, métricas de CPU e monitoramento de RAM em tempo real.
* **📋 Logs Integrados:** Visualização direta de `dmesg` e `journalctl` para diagnóstico rápido.

---

## 📸 Interface

> **Dica:** Adicione aqui um print da aba Dashboard e da aba USB Installer para chamar a atenção!

---

## 🚀 Como Iniciar


### 1. Dependências de Sistema (Debian/Ubuntu)
 O CoffeeCat utiliza ferramentas nativas do     Linux para operações de baixo nível:
 ```bash
 sudo apt install smartmontools grub2-common pv  wget lsblk


 2.dependencias do python 
pip install customtkinter psutil


 3.execução
sudo python3 coffeecat.py
