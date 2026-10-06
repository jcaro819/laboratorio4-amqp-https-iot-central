"""Analiza un .pcap (Ethernet/IPv4/TCP) y cuenta bytes reales en el cable hacia el hub.

Uso: python analyze_pcap.py <captura.pcap> <resumen.json> <salida.json>
El hub se toma de resumen.json y se resuelve por DNS; solo se cuentan los paquetes
hacia/desde esa(s) IP(s) (el trafico del DPS, otra IP, queda fuera).
bytes_wire = longitud IP total + 14 (cabecera Ethernet). payload = bytes TCP utiles (TLS).
"""
import json
import socket
import struct
import sys


def main(pcap, resumen, salida):
    info = json.load(open(resumen, encoding="utf-8"))
    hub_ips = {x[4][0] for x in socket.getaddrinfo(info["hub"], None, socket.AF_INET)}
    port = info["port"]
    data = open(pcap, "rb").read()
    magic = struct.unpack("<I", data[:4])[0]
    if magic in (0xA1B2C3D4, 0xA1B23C4D):
        endian = "<"
    else:
        endian = ">"
    nano = magic in (0xA1B23C4D, 0x4D3CB2A1)
    off, n = 24, len(data)
    t_first = t_last = None
    out = {"up_bytes": 0, "down_bytes": 0, "up_frames": 0, "down_frames": 0,
           "up_payload": 0, "down_payload": 0, "connections": 0}
    while off + 16 <= n:
        sec, frac, incl, _orig = struct.unpack(endian + "IIII", data[off:off + 16])
        pkt = data[off + 16: off + 16 + incl]
        off += 16 + incl
        if len(pkt) < 34 or struct.unpack("!H", pkt[12:14])[0] != 0x0800:
            continue
        ip = pkt[14:]
        ihl = (ip[0] & 0x0F) * 4
        if ip[9] != 6:
            continue
        total = struct.unpack("!H", ip[2:4])[0]
        src, dst = socket.inet_ntoa(ip[12:16]), socket.inet_ntoa(ip[16:20])
        tcp = ip[ihl:]
        sport, dport = struct.unpack("!HH", tcp[:4])
        flags = tcp[13]
        doff = (tcp[12] >> 4) * 4
        payload = total - ihl - doff
        if dst in hub_ips and dport == port:
            d = "up"
        elif src in hub_ips and sport == port:
            d = "down"
        else:
            continue
        if d == "up" and (flags & 0x02) and not (flags & 0x10):
            out["connections"] += 1
        out[f"{d}_bytes"] += total + 14
        out[f"{d}_frames"] += 1
        out[f"{d}_payload"] += payload
        t = sec + frac / (1e9 if nano else 1e6)
        t_first = t if t_first is None else t_first
        t_last = t
    out["total_bytes"] = out["up_bytes"] + out["down_bytes"]
    out["total_frames"] = out["up_frames"] + out["down_frames"]
    out["duration_s"] = round((t_last or 0) - (t_first or 0), 2)
    out["hub_ips"] = sorted(hub_ips)
    json.dump(out, open(salida, "w", encoding="utf-8"), indent=2)
    print("[WIRE]", json.dumps(out))


if __name__ == "__main__":
    main(*sys.argv[1:4])
