"""Lab 4 - baseline: MQTT explicito (paho) con el mismo dispositivo/condiciones que
AMQP y HTTPS, para que la tabla comparativa use medidas del MISMO entorno.

Mismo patron del Lab 3: DPS por HTTPS, MQTT 3.1.1 sobre TLS (8883), QoS 1.
La confirmacion que se mide es el PUBACK.
"""
import argparse
import json
import ssl
import sys
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from common import CsvLog, hub_sas_token, load_credentials, make_payload, payload_bytes, provision


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="lab4-mqtt")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--log", default="mediciones/mqtt.csv")
    ap.add_argument("--summary", default="mediciones/mqtt_resumen.json")
    a = ap.parse_args()

    id_scope, key = load_credentials(a.device)
    hub, t_dps = provision(id_scope, a.device, key)
    print(f"[DPS] hub asignado: {hub} ({t_dps*1000:.0f} ms)")

    connected = threading.Event()
    rc_box = {}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        rc_box["rc"] = reason_code
        connected.set()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=a.device, protocol=mqtt.MQTTv311)
    client.username_pw_set(f"{hub}/{a.device}/?api-version=2021-04-12",
                           hub_sas_token(hub, a.device, key, ttl_seconds=3600))
    client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.on_connect = on_connect

    t0 = time.perf_counter()
    client.connect(hub, 8883, keepalive=60)
    client.loop_start()
    if not connected.wait(30) or str(rc_box.get("rc")) not in ("Success", "0"):
        print("[MQTT] no se pudo conectar:", rc_box)
        sys.exit(2)
    t_conn = time.perf_counter() - t0
    print(f"[MQTT] conectado a {hub}:8883  conexion+CONNACK={t_conn*1000:.0f} ms")

    topic = f"devices/{a.device}/messages/events/"
    log = CsvLog(a.log)
    ok = 0
    for i in range(a.count):
        payload = make_payload()
        body = payload_bytes(payload)
        t = time.perf_counter()
        info = client.publish(topic, body, qos=1)
        try:
            info.wait_for_publish(timeout=30)
            ack_ms = (time.perf_counter() - t) * 1000
            status = "puback" if info.is_published() else "sin_puback"
        except Exception as e:  # noqa: BLE001
            ack_ms, status = (time.perf_counter() - t) * 1000, f"error:{type(e).__name__}"
        ok += status == "puback"
        log.row(protocol="MQTT", i=i + 1, ts_utc=datetime.now(timezone.utc).isoformat(),
                payload_bytes=len(body), ack_ms=round(ack_ms, 2), status=status)
        print(f"[MQTT] #{i+1} {payload} ack={ack_ms:.1f} ms status={status}")
        time.sleep(a.interval)

    client.loop_stop()
    client.disconnect()
    summary = {"protocol": "MQTT", "device": a.device, "hub": hub, "port": 8883,
               "dps_s": round(t_dps, 3), "connect_s": round(t_conn, 3), "sent": a.count, "accepted": ok}
    with open(a.summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("[RESUMEN]", json.dumps(summary))
    sys.exit(0 if ok == a.count else 1)


if __name__ == "__main__":
    main()
