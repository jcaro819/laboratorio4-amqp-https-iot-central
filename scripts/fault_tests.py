"""Lab 4 - pruebas de falla: que ve el desarrollador cuando la autenticacion falla.

Casos: (a) clave incorrecta (token firmado con otra clave), (b) token vencido.
Se usa un dispositivo propio de Lab 4 y un hub ya asignado (de los resumenes).
Salida: mediciones/fallas.json
"""
import base64
import json
import ssl
import threading
import time

import paho.mqtt.client as mqtt
import requests
from proton import SSLDomain
from proton.utils import BlockingConnection

from common import hub_sas_token, load_credentials
from amqp_proton import ssl_domain

HUB = json.load(open("/out/amqp_n1_resumen.json"))["hub"]
HUB_NAME = HUB.split(".")[0]
WRONG_KEY = base64.b64encode(b"x" * 32).decode()
res = {}


def tokens(dev):
    _, key = load_credentials(dev)
    return {"clave_incorrecta": hub_sas_token(HUB, dev, WRONG_KEY, 3600),
            "token_vencido": hub_sas_token(HUB, dev, key, -600)}


def amqp(dev, tok):
    t = time.perf_counter()
    try:
        c = BlockingConnection(f"amqps://{HUB}:5671", timeout=20, ssl_domain=ssl_domain(),
                               user=f"{dev}@sas.{HUB_NAME}", password=tok,
                               allowed_mechs="PLAIN", allow_insecure_mechs=True)
        s = c.create_sender(f"/devices/{dev}/messages/events")
        s.send(__import__("proton").Message(body=b"{}"), timeout=10)
        c.close()
        return {"resultado": "ACEPTADO (inesperado)"}
    except Exception as e:  # noqa: BLE001
        return {"resultado": f"{type(e).__name__}: {e}", "ms": round((time.perf_counter() - t) * 1000)}


def mqtt_(dev, tok):
    box, ev = {}, threading.Event()
    cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=dev, protocol=mqtt.MQTTv311)
    cl.username_pw_set(f"{HUB}/{dev}/?api-version=2021-04-12", tok)
    cl.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    cl.on_connect = lambda c, u, f, rc, p=None: (box.update(rc=str(rc)), ev.set())
    t = time.perf_counter()
    try:
        cl.connect(HUB, 8883, 60)
        cl.loop_start()
        ev.wait(20)
        cl.loop_stop()
        return {"resultado": f"CONNACK {box.get('rc', 'sin respuesta')}", "ms": round((time.perf_counter() - t) * 1000)}
    except Exception as e:  # noqa: BLE001
        return {"resultado": f"{type(e).__name__}: {e}", "ms": round((time.perf_counter() - t) * 1000)}


def https(dev, tok):
    t = time.perf_counter()
    r = requests.post(f"https://{HUB}/devices/{dev}/messages/events?api-version=2020-09-30",
                      data=b"{}", headers={"Authorization": tok, "Content-Type": "application/json"}, timeout=20)
    return {"resultado": f"HTTP {r.status_code}", "cuerpo": r.text[:300], "ms": round((time.perf_counter() - t) * 1000)}


for proto, dev, fn in [("AMQP", "lab4-amqp", amqp), ("MQTT", "lab4-mqtt", mqtt_), ("HTTPS", "lab4-https", https)]:
    res[proto] = {caso: fn(dev, tok) for caso, tok in tokens(dev).items()}
    print(proto, json.dumps(res[proto], ensure_ascii=False))
json.dump(res, open("/out/fallas.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
