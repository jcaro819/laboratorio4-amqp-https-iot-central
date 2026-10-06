#!/bin/sh
# Corre un cliente del Lab 4 mientras tcpdump captura el trafico TCP del contenedor.
# Uso: measure.sh <nombre> <cantidad> <script.py> [args extra del cliente...]
# Salidas en /out: <nombre>.pcap  <nombre>.csv  <nombre>_resumen.json  <nombre>_wire.json
name=$1; count=$2; script=$3; shift 3
rm -f /out/$name.csv
tcpdump -i eth0 -n -s 0 -w /out/$name.pcap tcp >/dev/null 2>&1 &
TP=$!
sleep 1
python "$script" --count "$count" --interval 1 --log /out/$name.csv --summary /out/${name}_resumen.json "$@"
rc=$?
sleep 2
kill -INT $TP 2>/dev/null; wait $TP 2>/dev/null
python analyze_pcap.py /out/$name.pcap /out/${name}_resumen.json /out/${name}_wire.json
exit $rc
