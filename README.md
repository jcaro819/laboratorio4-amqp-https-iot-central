# Laboratorio 4 — AMQP + HTTPS frente a MQTT hacia Azure IoT Central

**Autores:** Juan Felipe Caro Niño · Santiago Cabeza Méndez
**App IoT Central:** `UNAB-Ambiental — Monitoreo de Espacios Académicos` (`laboratorio1caro.azureiotcentral.com`)
**Informe (2 páginas):** [`informe/Informe_Laboratorio4_AMQP_HTTPS_vs_MQTT.pdf`](informe/Informe_Laboratorio4_AMQP_HTTPS_vs_MQTT.pdf)

Se publican las mismas 3 variables (`temperature`, `humidity`, `illuminance`) con tres protocolos distintos,
cada uno con su propio dispositivo de la plantilla «Nodo Ambiental de Aula (ESP32)»:

| Dispositivo | Protocolo | Script |
|---|---|---|
| `lab4-amqp`  | AMQP 1.0 sobre TLS, puerto 5671 (SASL PLAIN + SAS) | [`scripts/amqp_proton.py`](scripts/amqp_proton.py) |
| `lab4-https` | HTTPS REST, puerto 443 (tercer protocolo; modos keep-alive y 1 conexión/mensaje) | [`scripts/https_client.py`](scripts/https_client.py) |
| `lab4-mqtt`  | MQTT 3.1.1 sobre TLS, puerto 8883, QoS 1 (línea base) | [`scripts/mqtt_baseline.py`](scripts/mqtt_baseline.py) |

El SDK `azure-iot-device` de Python (2.14.0) no implementa AMQP, por eso se usa un cliente AMQP 1.0 explícito
con `python-qpid-proton`. Los tres clientes usan el módulo [`scripts/dps_sas.py`](scripts/dps_sas.py) (DPS por HTTPS + token SAS,
sin SDK) y las utilidades de [`scripts/common.py`](scripts/common.py).

## Estructura

```
scripts/      clientes (AMQP, HTTPS, MQTT), DPS/SAS, medición de bytes (analyze_pcap.py), pruebas de falla, resumen
mediciones/   CSV por mensaje, resúmenes JSON, capturas .pcap (TLS, sin contenido legible) y comparacion.md/.json
evidencias/   log de la campaña, verificación en IoT Central (cruce de 30 payloads por protocolo)
informe/      informe del laboratorio (HTML + PDF)
Dockerfile    imagen de medición: Python 3.12 + qpid-proton + paho + requests + tcpdump
run_all.sh    reproduce toda la campaña de medición (1 y 30 mensajes por protocolo)
```

## Cómo reproducir (sin secretos en el repo)

1. Crear en IoT Central tres dispositivos de la plantilla del Lab 3 y copiar la **clave primaria** de cada uno
   (panel *Conectar*) y el **ID Scope** de la app. Guardarlos fuera de git, en `.secrets/` (ignorada por `.gitignore`):

   ```
   .secrets/idscope.txt      # ID Scope de la app
   .secrets/lab4-amqp.key    # clave primaria del dispositivo lab4-amqp
   .secrets/lab4-https.key
   .secrets/lab4-mqtt.key
   ```

   (alternativa: variables de entorno `ID_SCOPE` y `PRIMARY_KEY` para un solo cliente).
2. Con Docker instalado, correr toda la campaña (construye la imagen, captura con `tcpdump` y calcula bytes en el cable):

   ```bash
   ./run_all.sh
   python scripts/compare.py        # genera mediciones/comparacion.md y .json
   ```
3. Un cliente suelto, por ejemplo AMQP, dentro del contenedor:

   ```bash
   docker run --rm -v "$PWD/scripts:/app/scripts:ro" -v "$PWD/.secrets:/app/.secrets:ro" -v "$PWD/mediciones:/out" \
     lab4-iot python amqp_proton.py --count 10 --interval 1 --log /out/prueba.csv --summary /out/prueba.json
   ```
4. Pruebas de falla de autenticación (clave incorrecta / token vencido en los tres protocolos):
   `python fault_tests.py` dentro del contenedor (resultado en `mediciones/fallas.json`).

Fuera de Docker (Windows/Linux) los clientes también corren con un `venv` (`pip install requests python-dotenv paho-mqtt python-qpid-proton`);
en Windows `python-qpid-proton` requiere `pip install --only-binary :all:`. La medición de bytes sí necesita Linux + `tcpdump`.

## Resultados (6 de octubre de 2026, 30 mensajes por protocolo, todos confirmados)

| Protocolo | ack medio (ms) | mediana | p95 | B/msj marginal | B de conexión (1 msj) |
|---|---|---|---|---|---|
| AMQP 1.0 (5671) | 233 | 213 | 312 | 474 | 9 915 |
| MQTT 3.1.1 (8883) | 212 | 198 | 242 | 417 | 7 815 |
| HTTPS keep-alive (443) | 214 | 208 | 245 | 1 069 | 7 509 |
| HTTPS 1 conexión/msj (443) | 633 | 619 | 818 | 7 742 | 7 505 |

Payload JSON ≈ 56 B. Bytes medidos en la interfaz del contenedor (Ethernet + IP + TCP + TLS + ACKs), sin el DPS.
La comparación completa (confiabilidad, depuración, firewalls, soporte en microcontroladores y recomendaciones) está en el informe.

## Notas y límites

- **Entorno:** la VM `laboratorio3caro` fue eliminada el 2026-10-02 y la suscripción «Azure for Students» está deshabilitada,
  por lo que las pruebas se ejecutaron desde un contenedor Docker en el PC del estudiante (red residencial), no desde la VM.
  IoT Central siguió aceptando telemetría de dispositivos.
- Una corrida de 30 mensajes por protocolo y una sola red: las diferencias de latencia entre MQTT/AMQP/HTTPS keep-alive están dentro del ruido (~1 RTT ≈ 190–200 ms).
- Variantes WebSocket (MQTT-WS, AMQP-WS), hardware real y Wokwi no se midieron en este laboratorio; esas filas del informe son documentales.
- Los dispositivos del Laboratorio 3 y sus datos no se modificaron: el Lab 4 usa dispositivos nuevos (`lab4-*`) en la misma app.
