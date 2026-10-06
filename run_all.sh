#!/bin/sh
# Reproduce TODAS las mediciones del Lab 4 desde el host (requiere Docker y .secrets/).
# Para cada protocolo: 1 mensaje (costo de conexion) y 30 mensajes (costo marginal por mensaje).
cd "$(dirname "$0")"
docker build -t lab4-iot . || exit 1
mkdir -p mediciones
run() { # nombre cantidad script [args]
  MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$(pwd -W 2>/dev/null || pwd)/scripts:/app/scripts:ro" \
    -v "$(pwd -W 2>/dev/null || pwd)/.secrets:/app/.secrets:ro" \
    -v "$(pwd -W 2>/dev/null || pwd)/mediciones:/out" \
    lab4-iot sh measure.sh "$@"
}
for n in 1 30; do
  run amqp_n$n        $n amqp_proton.py
  run mqtt_n$n        $n mqtt_baseline.py
  run https_session_n$n $n https_client.py --mode session
  run https_new_n$n   $n https_client.py --mode new
done
