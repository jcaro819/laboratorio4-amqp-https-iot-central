"""Lab 4 - Etapa 1: telemetria hacia IoT Central por AMQP 1.0 (puerto 5671, TLS).

Cliente AMQP explicito con python-qpid-proton (el SDK azure-iot-device de Python
solo habla MQTT / MQTT-WS, por eso se baja un nivel).

Flujo:
  1. DPS por HTTPS -> hub asignado.
  2. TCP + TLS 1.2 al hub:5671, SASL PLAIN con usuario  <deviceId>@sas.<hub>
     y como contrasena un token SAS del dispositivo (sr=<hub>/devices/<id>).
  3. Enlace emisor (sender link) a /devices/<id>/messages/events.
  4. Cada mensaje es un transfer AMQP; el hub responde con una disposicion
     "accepted" -> esa es la confirmacion que se mide.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from proton import Message, SSLDomain
from proton.utils import BlockingConnection

from common import CsvLog, hub_sas_token, load_credentials, make_payload, payload_bytes, provision

CA_CANDIDATES = ["/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt"]


def ssl_domain():
    d = SSLDomain(SSLDomain.MODE_CLIENT)
    for ca in CA_CANDIDATES:
        if os.path.exists(ca):
            d.set_trusted_ca_db(ca)
            break
    d.set_peer_authentication(SSLDomain.VERIFY_PEER_NAME)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="lab4-amqp")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--log", default="mediciones/amqp.csv")
    ap.add_argument("--summary", default="mediciones/amqp_resumen.json")
    a = ap.parse_args()

    id_scope, key = load_credentials(a.device)
    hub, t_dps = provision(id_scope, a.device, key)
    hub_name = hub.split(".")[0]
    print(f"[DPS] hub asignado: {hub} ({t_dps*1000:.0f} ms)")

    token = hub_sas_token(hub, a.device, key, ttl_seconds=3600)
    t0 = time.perf_counter()
    conn = BlockingConnection(
        f"amqps://{hub}:5671",
        timeout=30,
        ssl_domain=ssl_domain(),
        user=f"{a.device}@sas.{hub_name}",
        password=token,
        allowed_mechs="PLAIN",
        allow_insecure_mechs=True,
    )
    t_conn = time.perf_counter() - t0
    t1 = time.perf_counter()
    sender = conn.create_sender(f"/devices/{a.device}/messages/events")
    t_link = time.perf_counter() - t1
    print(f"[AMQP] conectado a {hub}:5671  conexion+SASL={t_conn*1000:.0f} ms  enlace={t_link*1000:.0f} ms")

    log = CsvLog(a.log)
    ok = 0
    for i in range(a.count):
        payload = make_payload()
        body = payload_bytes(payload)
        msg = Message(body=body, content_type="application/json", content_encoding="utf-8")
        msg.inferred = True  # cuerpo como seccion Data (lo que espera IoT Hub)
        t = time.perf_counter()
        try:
            delivery = sender.send(msg, timeout=30)
            ack_ms = (time.perf_counter() - t) * 1000
            state = str(delivery.remote_state) if delivery is not None else "None"
            status = "accepted" if "ACCEPTED" in state.upper() or state == "36" else state
        except Exception as e:  # noqa: BLE001
            ack_ms, status = (time.perf_counter() - t) * 1000, f"error:{type(e).__name__}"
        ok += status == "accepted"
        log.row(protocol="AMQP", i=i + 1, ts_utc=datetime.now(timezone.utc).isoformat(),
                payload_bytes=len(body), ack_ms=round(ack_ms, 2), status=status)
        print(f"[AMQP] #{i+1} {payload} ack={ack_ms:.1f} ms status={status}")
        time.sleep(a.interval)

    conn.close()
    summary = {"protocol": "AMQP", "device": a.device, "hub": hub, "port": 5671,
               "dps_s": round(t_dps, 3), "connect_s": round(t_conn, 3), "link_s": round(t_link, 3),
               "sent": a.count, "accepted": ok}
    with open(a.summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("[RESUMEN]", json.dumps(summary))
    sys.exit(0 if ok == a.count else 1)


if __name__ == "__main__":
    main()
