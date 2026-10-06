"""Utilidades compartidas por los 3 clientes del Lab 4 (MQTT, AMQP, HTTPS).

Credenciales: variables de entorno ID_SCOPE, DEVICE_ID, PRIMARY_KEY
(o archivos en .secrets/ cuando se corre fuera de contenedor).
"""
import csv
import json
import os
import random
import time
from pathlib import Path

from dps_sas import hub_sas_token, provision_device

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"


def load_credentials(device_id: str):
    id_scope = os.environ.get("ID_SCOPE")
    key = os.environ.get("PRIMARY_KEY")
    if not id_scope and (SECRETS / "idscope.txt").exists():
        id_scope = (SECRETS / "idscope.txt").read_text(encoding="utf-8-sig").strip()
    if not key and (SECRETS / f"{device_id}.key").exists():
        key = (SECRETS / f"{device_id}.key").read_text(encoding="utf-8-sig").strip()
    if not id_scope or not key:
        raise SystemExit(f"Faltan credenciales para {device_id} (ID_SCOPE / PRIMARY_KEY)")
    return id_scope, key


def provision(id_scope: str, device_id: str, key: str):
    """DPS por HTTPS. Devuelve (hostname_del_hub, segundos_que_tardo)."""
    t0 = time.perf_counter()
    result = provision_device(id_scope, device_id, key)
    return result["assigned_hub"], time.perf_counter() - t0


def make_payload():
    """Las mismas 3 variables que el Lab 3 (plantilla Nodo Ambiental de Aula)."""
    return {
        "temperature": round(random.uniform(16, 32), 1),
        "humidity": round(random.uniform(35, 70), 1),
        "illuminance": round(random.uniform(100, 900), 1),
    }


def payload_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


class CsvLog:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def row(self, **fields):
        new = not self.path.exists()
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(fields.keys()))
            if new:
                w.writeheader()
            w.writerow(fields)


__all__ = ["load_credentials", "provision", "make_payload", "payload_bytes", "CsvLog", "hub_sas_token"]
