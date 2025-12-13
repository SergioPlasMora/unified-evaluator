# 📊 Descripción de las Métricas del Load Test

## Summary (Resumen)

| Métrica | Descripción |
|---------|-------------|
| **Backend** | El sistema que se está evaluando (system1, system2, system3) |
| **Pattern** | Patrón de comunicación: `sync` (espera respuesta completa) o `stream` (datos progresivos) |
| **Duration** | Tiempo total que tardó en completarse todo el load test |
| **Total Requests** | Número total de solicitudes enviadas |
| **Successful** | Cantidad de requests exitosas |
| **Failed** | Cantidad de requests fallidas |
| **Throughput** | Requests por segundo - **Mayor = mejor** |
| **Data Transferred** | Total de datos recibidos durante el test |

## Latency Statistics (Estadísticas de Latencia)

| Métrica | Descripción |
|---------|-------------|
| **Average** | Latencia promedio (ms) |
| **Min** | Latencia más baja (mejor caso) |
| **Max** | Latencia más alta (peor caso) |
| **P50** | Percentil 50 - El 50% de requests tardaron menos (mediana) |
| **P95** | Percentil 95 - El 95% tardaron menos ("peor caso típico") |
| **P99** | Percentil 99 - Mide outliers extremos |
| **Avg TTFB** | Time To First Byte - Tiempo hasta recibir el primer byte |

## 🎯 Métricas Más Importantes

1. **Throughput (req/s)** → Capacidad del sistema
2. **TTFB (ms)** → Qué tan rápido responde inicialmente
3. **P95 y P99 (ms)** → Consistencia/estabilidad

---

# Sistema 1: FastApi + SSE utilizando el patron sync

╭───────────────────╮
│ Unified Evaluator │
│ Backend: system1  │
╰───────────────────╯
2025-12-12 19:38:47,003 - unified-evaluator - INFO - Starting load test: 1000 requests, 1000 concurrent
  Progress: 1000/1000

Load Test Results
              Summary
╭──────────────────┬──────────────╮
│ Metric           │ Value        │
├──────────────────┼──────────────┤
│ Backend          │ system1      │
│ Pattern          │ sync         │
│ Duration         │ 9.16 s       │
│ Total Requests   │ 1000         │
│ Successful       │ 1000         │
│ Failed           │ 0            │
│ Throughput       │ 109.22 req/s │
│ Data Transferred │ 1006.41 MB   │
╰──────────────────┴──────────────╯
Latency Statistics (ms)
╭───────────┬─────────╮
│ Statistic │ Time    │
├───────────┼─────────┤
│ Average   │ 4625.33 │
│ Min       │ 262.42  │
│ Max       │ 7584.91 │
│ P50       │ 4774.98 │
│ P95       │ 7375.27 │
│ P99       │ 7503.31 │
│ Avg TTFB  │ 4625.33 │
╰───────────┴─────────╯


# Sistema 1: FastApi + SSE utilizando el patron stream

╭───────────────────╮
│ Unified Evaluator │
│ Backend: system1  │
╰───────────────────╯
2025-12-12 19:38:59,966 - unified-evaluator - INFO - Starting load test: 1000 requests, 1000 concurrent
  Progress: 1000/1000

Load Test Results
             Summary
╭──────────────────┬─────────────╮
│ Metric           │ Value       │
├──────────────────┼─────────────┤
│ Backend          │ system1     │
│ Pattern          │ stream      │
│ Duration         │ 16.33 s     │
│ Total Requests   │ 1000        │
│ Successful       │ 1000        │
│ Failed           │ 0           │
│ Throughput       │ 61.25 req/s │
│ Data Transferred │ 1006.41 MB  │
╰──────────────────┴─────────────╯
Latency Statistics (ms)
╭───────────┬──────────╮
│ Statistic │ Time     │
├───────────┼──────────┤
│ Average   │ 8546.84  │
│ Min       │ 505.98   │
│ Max       │ 14535.08 │
│ P50       │ 8650.70  │
│ P95       │ 14305.81 │
│ P99       │ 14439.36 │
│ Avg TTFB  │ 8104.36  │
╰───────────┴──────────╯


# Sistema 2: Arrow Flight + Fastapi sync 

╭───────────────────╮
│ Unified Evaluator │
│ Backend: system2  │
╰───────────────────╯
2025-12-12 21:20:27,577 - unified-evaluator - INFO - Starting load test: 1000 requests, 1000 concurrent
  Progress: 1000/1000

Load Test Results
             Summary
╭──────────────────┬─────────────╮
│ Metric           │ Value       │
├──────────────────┼─────────────┤
│ Backend          │ system2     │
│ Pattern          │ sync        │
│ Duration         │ 76.33 s     │
│ Total Requests   │ 1000        │
│ Successful       │ 1000        │
│ Failed           │ 0           │
│ Throughput       │ 13.10 req/s │
│ Data Transferred │ 896.94 MB   │
╰──────────────────┴─────────────╯
Latency Statistics (ms)
╭───────────┬──────────╮
│ Statistic │ Time     │
├───────────┼──────────┤
│ Average   │ 42469.97 │
│ Min       │ 8363.82  │
│ Max       │ 76153.87 │
│ P50       │ 45574.30 │
│ P95       │ 75997.83 │
│ P99       │ 76087.70 │
│ Avg TTFB  │ 588.21   │
╰───────────┴──────────╯


# Sistema 2: Arrow Flight + Fastapi stream

╭───────────────────╮
│ Unified Evaluator │
│ Backend: system2  │
╰───────────────────╯
2025-12-12 21:26:51,821 - unified-evaluator - INFO - Starting load test: 1000 requests, 1000 concurrent
  Progress: 1000/1000

Load Test Results
             Summary
╭──────────────────┬─────────────╮
│ Metric           │ Value       │
├──────────────────┼─────────────┤
│ Backend          │ system2     │
│ Pattern          │ stream      │
│ Duration         │ 74.59 s     │
│ Total Requests   │ 1000        │
│ Successful       │ 1000        │
│ Failed           │ 0           │
│ Throughput       │ 13.41 req/s │
│ Data Transferred │ 898.32 MB   │
╰──────────────────┴─────────────╯
Latency Statistics (ms)
╭───────────┬──────────╮
│ Statistic │ Time     │
├───────────┼──────────┤
│ Average   │ 42173.58 │
│ Min       │ 6691.84  │
│ Max       │ 74413.88 │
│ P50       │ 43410.57 │
│ P95       │ 74114.83 │
│ P99       │ 74346.05 │
│ Avg TTFB  │ 42162.79 │
╰───────────┴──────────╯



# Sistema 3: Apache Arrow Flight + Node.js patron sync

╭───────────────────╮
│ Unified Evaluator │
│ Backend: system3  │
╰───────────────────╯
2025-12-12 19:35:19,460 - unified-evaluator - INFO - Starting load test: 1000 requests, 1000 concurrent
  Progress: 1000/1000

Load Test Results
              Summary
╭──────────────────┬──────────────╮
│ Metric           │ Value        │
├──────────────────┼──────────────┤
│ Backend          │ system3      │
│ Pattern          │ stream       │
│ Duration         │ 7.42 s       │
│ Total Requests   │ 1000         │
│ Successful       │ 1000         │
│ Failed           │ 0            │
│ Throughput       │ 134.72 req/s │
│ Data Transferred │ 898.32 MB    │
╰──────────────────┴──────────────╯
Latency Statistics (ms)
╭───────────┬─────────╮
│ Statistic │ Time    │
├───────────┼─────────┤
│ Average   │ 4318.59 │
│ Min       │ 1255.29 │
│ Max       │ 7362.77 │
│ P50       │ 4314.54 │
│ P95       │ 6923.11 │
│ P99       │ 7274.05 │
│ Avg TTFB  │ 4277.38 │
╰───────────┴─────────╯



# Sistema 3: Apache Arrow Flight + Node.js patron stream
╭───────────────────╮
│ Unified Evaluator │
│ Backend: system3  │
╰───────────────────╯
2025-12-12 19:35:59,104 - unified-evaluator - INFO - Starting load test: 1000 requests, 1000 concurrent
  Progress: 1000/1000

Load Test Results
              Summary
╭──────────────────┬──────────────╮
│ Metric           │ Value        │
├──────────────────┼──────────────┤
│ Backend          │ system3      │
│ Pattern          │ sync         │
│ Duration         │ 7.16 s       │
│ Total Requests   │ 1000         │
│ Successful       │ 1000         │
│ Failed           │ 0            │
│ Throughput       │ 139.58 req/s │
│ Data Transferred │ 898.32 MB    │
╰──────────────────┴──────────────╯
Latency Statistics (ms)
╭───────────┬─────────╮
│ Statistic │ Time    │
├───────────┼─────────┤
│ Average   │ 4153.93 │
│ Min       │ 1198.74 │
│ Max       │ 7026.66 │
│ P50       │ 4149.04 │
│ P95       │ 6719.73 │
│ P99       │ 6990.70 │
│ Avg TTFB  │ 1032.38 │
╰───────────┴─────────╯

---

# 📈 Tabla Comparativa

| Sistema | Protocolo | Pattern | Throughput | Latencia P50 | TTFB | Duración |
|---------|-----------|---------|------------|--------------|------|----------|
| System1 (FastAPI+SSE) | HTTP/SSE | sync | **109 req/s** | 4.7s | 4.6s | 9.16s |
| System1 (FastAPI+SSE) | HTTP/SSE | stream | 61 req/s | 8.6s | 8.1s | 16.33s |
| System2 (Python+Flight) | gRPC | sync | 13 req/s | 45.5s | **0.6s** | 76.33s |
| System2 (Python+Flight) | gRPC | stream | 13 req/s | 43.4s | 42.1s | 74.59s |
| System3 (Node+Flight) | gRPC | sync | **140 req/s** | **4.1s** | 1.0s | **7.16s** |
| System3 (Node+Flight) | gRPC | stream | 135 req/s | 4.3s | 4.3s | 7.42s |

---

# 🔍 Análisis: ¿Por qué System2 (Python) es lento?

## El Problema: Incompatibilidad Arquitectónica

El Gateway Python combina dos modelos de concurrencia incompatibles:

```
Cliente gRPC ──► PyArrow Flight Server ──► WebSocket Manager ──► Data Connector
                    (Thread Pool)            (asyncio event loop)
```

### Threads vs Asyncio

| Componente | Modelo | Problema |
|------------|--------|----------|
| **PyArrow Flight** | Thread Pool (4-10 threads) | Espera bloqueante |
| **FastAPI/Uvicorn** | asyncio (1 event loop) | Cuello de botella |

### Lo que sucede con 1000 requests concurrentes:

1. gRPC recibe 1000 requests → las envía a su pool de threads
2. Cada thread llama a `run_coroutine_threadsafe()` → envía trabajo al event loop
3. El event loop (1 solo hilo) procesa las tareas **secuencialmente**
4. Los threads gRPC esperan bloqueados

```
Threads gRPC:  ─────────[espera bloqueante]─────────────────→
Event Loop:    ─[t1]─[t2]─[t3]─...─[t1000]→ (secuencial)
```

### ¿Por qué Node.js no tiene este problema?

Node.js usa **un solo modelo de concurrencia** (event loop nativo). No hay conversión entre threads y async, todo fluye naturalmente.

## Conclusión

| Aspecto | Veredicto |
|---------|-----------|
| Lógica de programación | ✅ Correcta (0% errores, toda la data transferida) |
| Causa del bajo rendimiento | ❌ Incompatibilidad arquitectónica PyArrow Flight + asyncio |
| Solución recomendada | Usar Node.js Gateway para alto throughput |

> **Nota**: El TTFB bajo de Python (588ms) demuestra que el servidor responde rápido inicialmente. El cuello de botella está en la transferencia de datos bajo alta concurrencia.

