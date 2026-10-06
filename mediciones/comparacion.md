| Protocolo | ack medio (ms) | mediana | p95 | 1.er msj (ms) | B/msj marginal | tramas/msj | B totales 1 msj | conex. TCP en 30 | entregados |
|---|---|---|---|---|---|---|---|---|---|
| AMQP 1.0 (5671) | 233.2 | 213.4 | 312.3 | 204.9 | 474 | 4.0 | 9915 | 1 | 30/30 |
| MQTT 3.1.1 (8883) | 212.5 | 198.4 | 241.5 | 200.7 | 417 | 3.9 | 7815 | 1 | 30/30 |
| HTTPS keep-alive (443) | 213.7 | 208.3 | 245.3 | 556.9 | 1069 | 5.6 | 7509 | 1 | 30/30 |
| HTTPS 1 conexion/msj (443) | 632.6 | 619.2 | 818.1 | 588.9 | 7742 | 24.0 | 7505 | 30 | 30/30 |

Payload JSON medio: 56 B (temperature, humidity, illuminance).
