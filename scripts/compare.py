"""Resume las mediciones del Lab 4 -> mediciones/comparacion.json y .md (stdlib solamente)."""
import csv
import json
import statistics as st
from pathlib import Path

M = Path(__file__).resolve().parent.parent / "mediciones"
RUNS = [("AMQP 1.0 (5671)", "amqp"), ("MQTT 3.1.1 (8883)", "mqtt"),
        ("HTTPS keep-alive (443)", "https_session"), ("HTTPS 1 conexion/msj (443)", "https_new")]


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


out, rows = {}, []
PAYLOAD = st.mean(int(r["payload_bytes"]) for r in csv.DictReader(open(M / "amqp_n30.csv", encoding="utf-8")))
for label, key in RUNS:
    lat = [float(r["ack_ms"]) for r in csv.DictReader(open(M / f"{key}_n30.csv", encoding="utf-8"))]
    steady = lat[1:]  # sin el 1.er mensaje (incluye costos de arranque del enlace)
    w1 = json.load(open(M / f"{key}_n1_wire.json"))
    w30 = json.load(open(M / f"{key}_n30_wire.json"))
    r1 = json.load(open(M / f"{key}_n1_resumen.json"))
    marg = (w30["total_bytes"] - w1["total_bytes"]) / 29
    marg_fr = (w30["total_frames"] - w1["total_frames"]) / 29
    d = {
        "ack_ms_media": round(st.mean(steady), 1), "ack_ms_mediana": round(st.median(steady), 1),
        "ack_ms_p95": round(pct(steady, 95), 1), "ack_ms_min": round(min(steady), 1), "ack_ms_max": round(max(steady), 1),
        "ack_ms_primer_mensaje": round(lat[0], 1),
        "bytes_conexion_1msj": w1["total_bytes"], "frames_conexion_1msj": w1["total_frames"],
        "bytes_marginales_por_msj": round(marg), "frames_marginales_por_msj": round(marg_fr, 1),
        "overhead_x_payload": round(marg / PAYLOAD, 1),
        "conexiones_tcp_en_30": w30["connections"],
        "conexion_s": r1.get("connect_s"), "enlace_s": r1.get("link_s"),
        "aceptados_30": json.load(open(M / f"{key}_n30_resumen.json"))["accepted"],
    }
    out[label] = d
    rows.append((label, d))
sizes = [int(r["payload_bytes"]) for r in csv.DictReader(open(M / "amqp_n30.csv", encoding="utf-8"))]
out["_payload_bytes_medio"] = round(st.mean(sizes), 1)
json.dump(out, open(M / "comparacion.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
md = ["| Protocolo | ack medio (ms) | mediana | p95 | 1.er msj (ms) | B/msj marginal | tramas/msj | B totales 1 msj | conex. TCP en 30 | entregados |",
      "|---|---|---|---|---|---|---|---|---|---|"]
for l, d in rows:
    md.append(f"| {l} | {d['ack_ms_media']} | {d['ack_ms_mediana']} | {d['ack_ms_p95']} | {d['ack_ms_primer_mensaje']} | "
              f"{d['bytes_marginales_por_msj']} | {d['frames_marginales_por_msj']} | {d['bytes_conexion_1msj']} | "
              f"{d['conexiones_tcp_en_30']} | {d['aceptados_30']}/30 |")
md.append(f"\nPayload JSON medio: {out['_payload_bytes_medio']} B (temperature, humidity, illuminance).")
(M / "comparacion.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
