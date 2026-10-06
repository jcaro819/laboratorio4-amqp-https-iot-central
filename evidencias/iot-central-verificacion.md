# Verificación en IoT Central (UNAB-Ambiental — laboratorio1caro.azureiotcentral.com)

Fecha: 2026-10-06 (hora local de IoT Central, 8:02–8:08). Plantilla de los 3 dispositivos:
"Nodo Ambiental de Aula (ESP32)" (variables `temperature`, `humidity`, `illuminance`).

Método: tras cada corrida se abrió **Dispositivos → <dispositivo> → Datos sin procesar** y se cruzaron
programáticamente (JavaScript en la página) los payloads enviados (`enviados_n30.json`, extraídos del log de la
corrida) contra las filas "Telemetría" que IoT Central muestra (humedad, iluminancia, temperatura).

| Dispositivo | Protocolo | Corrida | Filas "Telemetría" visibles | Enviados | Coinciden exactamente |
|---|---|---|---|---|---|
| lab4-amqp  | AMQP 1.0 / TLS 5671 | 30 mensajes | 34 (3 de prueba + 1 + 30) | 30 | **30 / 30** |
| lab4-mqtt  | MQTT 3.1.1 / TLS 8883 | 30 mensajes | 34 | 30 | **30 / 30** |
| lab4-https | HTTPS 443 (keep-alive y 1 conexión/msj) | 30 + 30 mensajes | 49 | 60 | **49 / 49 visibles** |

Nota HTTPS: la vista de datos sin procesar solo lista los últimos ~49 eventos; los 11 más antiguos de la corrida
keep-alive quedaron fuera de esa ventana (todos los visibles coinciden; el cliente recibió HTTP 204 en los 60).

## Primera prueba AMQP (3 mensajes) — transcripción de "Datos sin procesar"

```
lab4-amqp  | Última recepción de datos: 6/10/2026, 8:02:45 | Estado: Aprovisionado
Marca de tiempo       Tipo de mensaje          Humedad  Iluminancia  Temperatura
6/10/2026, 8:02:46    Dispositivo desconectado
6/10/2026, 8:02:45    Telemetría               41.4     518.2        17
6/10/2026, 8:02:44    Telemetría               68.5     391.1        21.6
6/10/2026, 8:02:43    Telemetría               48.9     377.1        31.5
6/10/2026, 8:02:43    Dispositivo conectado
```
Enviados por el cliente AMQP (ver `log_campana_mediciones.txt` / consola):
`{'temperature': 31.5, 'humidity': 48.9, 'illuminance': 377.1}`, `{21.6, 68.5, 391.1}`, `{17.0, 41.4, 518.2}` → idénticos.

## Corrida AMQP de 30 mensajes (extracto, más reciente primero)

```
6/10/2026, 8:05:57  Dispositivo desconectado
6/10/2026, 8:05:56  Telemetría  56.8  567.2  27.2
6/10/2026, 8:05:55  Telemetría  66.8  171.9  28.2
6/10/2026, 8:05:54  Telemetría  68    844.9  23.7
   ... (30 filas, 8:05:22 a 8:05:56) ...
6/10/2026, 8:05:20  Dispositivo conectado
```

El evento "Dispositivo conectado / desconectado" lo genera IoT Hub al abrir/cerrar la conexión AMQP/MQTT;
con HTTPS no existe conexión persistente, por eso lab4-https no registra esos eventos.

## Hallazgo operativo
La suscripción "Azure for Students" aparece *Disabled* (sin crédito), pero la telemetría de dispositivos
**sigue siendo aceptada y mostrada** por la aplicación IoT Central existente (creada antes del bloqueo).
Lo que no se pudo hacer es crear recursos nuevos (la creación de una app nueva falló con 500.020.018.008).
