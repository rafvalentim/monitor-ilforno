#!/usr/bin/env python3
"""
Monitor de vagas - Il Forno Artesan (GetIn)
-------------------------------------------
Bate no endpoint interno de disponibilidade do GetIn e te avisa (ntfy.sh)
quando aparecer data nova. Endpoint e publico (sem token), entao e simples.

Uso:
    pip install requests
    python monitor_ilforno.py          # roda em loop (PC ligado)
    python monitor_ilforno.py --once   # roda 1x e sai (pra cron/GitHub Actions)
"""

import os
import sys
import time
import json
import random
from pathlib import Path

import requests

# ============================================================
# CONFIG
# ============================================================

UNIT_ID = "e63R441v"        # id do Il Forno na URL
PEOPLE = 2                  # nº de pessoas da reserva

API_URL = f"https://user.getinapis.com/reservation/v1/units/{UNIT_ID}/schedules/available-dates"
PARAMS = {"people": PEOPLE}

# Headers que o site manda. Sem Authorization (endpoint publico).
# Mantive Origin/Referer porque o servidor pode validar a origem.
HEADERS = {
    "Accept": "application/json",
    "Origin": "https://reservation.getin.app",
    "Referer": "https://reservation.getin.app/",
    "X-Referrer": "https://www.getin.app/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
}

INTERVALO = 300             # seg entre checagens no modo loop (5 min). Seja educado.
JITTER = 60                 # variacao aleatoria

# Notificacao via ntfy.sh. Em repo publico, defina NTFY_TOPIC como Secret no
# GitHub (nao deixe no codigo). Local, pode exportar a variavel ou trocar o fallback.
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "ilforno-vagas-troque-isso-9x7k2")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

STATE_FILE = Path("ultimo_estado.json")


def buscar_disponibilidade():
    r = requests.get(API_URL, headers=HEADERS, params=PARAMS, timeout=20)
    r.raise_for_status()
    return r.json()


def extrair_vagas(payload):
    """Retorna lista de strings com as datas disponiveis. [] = esgotado."""
    return ["TESTE - se chegou isso, ta funcionando! (remover esta linha)"]
    dates = (payload or {}).get("data", {}).get("dates", []) or []
    vagas = []
    for d in dates:
        if isinstance(d, dict):
            rotulo = d.get("date") or d.get("day") or json.dumps(d, ensure_ascii=False)
            vagas.append(str(rotulo))
        else:
            vagas.append(str(d))
    return vagas


def notificar(vagas):
    msg = "Abriu vaga no Il Forno!\n" + "\n".join(vagas)
    try:
        requests.post(
            NTFY_URL,
            data=msg.encode("utf-8"),
            headers={
                "Title": "Il Forno Artesan",
                "Priority": "high",
                "Tags": "pizza",
                "Click": "https://www.getin.app/joao-pessoa/il-forno-artesan",
            },
            timeout=10,
        )
    except Exception as e:
        print("Falha ao notificar:", e)


def carregar_estado():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def salvar_estado(vagas):
    STATE_FILE.write_text(json.dumps(sorted(vagas)))


def checar(visto):
    """Faz uma checagem; avisa se houver vaga nova. Retorna o set atual."""
    payload = buscar_disponibilidade()
    vagas = set(extrair_vagas(payload))
    novas = vagas - visto
    if novas:
        print("NOVAS VAGAS:", sorted(novas))
        notificar(sorted(novas))
    else:
        print(time.strftime("%H:%M"), f"- sem novidade ({len(vagas)} vagas)")
    salvar_estado(vagas)
    return vagas


def main():
    once = "--once" in sys.argv
    visto = carregar_estado()
    if once:
        checar(visto)
        return
    print(f"Monitorando a cada ~{INTERVALO}s. Ctrl+C pra parar.")
    while True:
        try:
            visto = checar(visto)
        except Exception as e:
            print("Erro:", e)
        time.sleep(INTERVALO + random.randint(0, JITTER))


if __name__ == "__main__":
    main()
