"""Lab 4 - Etapa 2: tercer protocolo = HTTPS (REST) hacia IoT Hub / IoT Central.

POST https://<hub>/devices/<id>/messages/events?api-version=2020-09-30
  Authorization: <token SAS del dispositivo>
  Content-Type: application/json
-> 204 No Content cuando el hub acepta el mensaje.

Dos modos para entender el costo real de "sin conexion persistente":
  --mode session : requests.Session (keep-alive; reusa TCP+TLS)
  --mode new     : una conexion TCP+TLS nueva por cada mensaje
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone

import requests

from common import CsvLog, hub_sas_token, load_credentials, make_payload, payload_bytes, provision


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="lab4-https")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--mode", choices=["session", "new"], default="session")
    ap.add_argument("--log", default=None)
    ap.add_argument("--summary", default=None)
    a = ap.parse_args()
    a.log = a.log or f"mediciones/https_{a.mode}.csv"
    a.summary = a.summary or f"mediciones/https_{a.mode}_resumen.json"

    id_scope, key = load_credentials(a.device)
    hub, t_dps = provision(id_scope, a.device, key)
    print(f"[DPS] hub asignado: {hub} ({t_dps*1000:.0f} ms)")

    token = hub_sas_token(hub, a.device, key, ttl_seconds=3600)
    url = f"https://{hub}/devices/{a.device}/messages/events?api-version=2020-09-30"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    session = requests.Session() if a.mode == "session" else None

    log = CsvLog(a.log)
    ok = 0
    for i in range(a.count):
        payload = make_payload()
        body = payload_bytes(payload)
        t = time.perf_counter()
        try:
            r = (session or requests).post(url, data=body, headers=headers, timeout=30)
            ack_ms = (time.perf_counter() - t) * 1000
            status = str(r.status_code)
            good = r.status_code == 204
        except Exception as e:  # noqa: BLE001
            ack_ms, status, good = (time.perf_counter() - t) * 1000, f"error:{type(e).__name__}", False
        ok += good
        log.row(protocol=f"HTTPS-{a.mode}", i=i + 1, ts_utc=datetime.now(timezone.utc).isoformat(),
                payload_bytes=len(body), ack_ms=round(ack_ms, 2), status=status)
        print(f"[HTTPS-{a.mode}] #{i+1} {payload} ack={ack_ms:.1f} ms HTTP {status}")
        time.sleep(a.interval)

    summary = {"protocol": f"HTTPS-{a.mode}", "device": a.device, "hub": hub, "port": 443,
               "dps_s": round(t_dps, 3), "sent": a.count, "accepted": ok}
    with open(a.summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("[RESUMEN]", json.dumps(summary))
    sys.exit(0 if ok == a.count else 1)


if __name__ == "__main__":
    main()
