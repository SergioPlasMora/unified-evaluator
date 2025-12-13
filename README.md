# Unified Evaluator

Cliente unificado para evaluar los 3 sistemas backend de comunicación con métricas consistentes.

## Instalación

```bash
cd unified-evaluator
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Backends Disponibles

| Backend | Sistema | Protocolos | Puerto |
|---------|---------|------------|--------|
| `system1` | luzzi-core-im-enrutador | REST + SSE | 8000 |
| `system2` | enrutador-gateway (Python) | Arrow Flight gRPC | 8080/8815 |
| `system3` | enrutador-gateway-node | Arrow Flight gRPC | 8081/8815 |

## Comandos

### Health Check

```bash
# Verificar conexión a cada sistema
python main.py --backend system1 health
python main.py --backend system2 health
python main.py --backend system3 health
```

### Listar Conectores

```bash
python main.py --backend system1 list
python main.py --backend system2 list
python main.py --backend system3 list
```

### Query Individual

```bash
# Sistema 1 (REST/SSE) - usa MAC address
python main.py --backend system1 query cc-28-aa-cd-5c-74 dataset_1mb.csv
python main.py --backend system1 query cc-28-aa-cd-5c-74 dataset_1mb.csv --pattern stream
python main.py --backend system1 query cc-28-aa-cd-5c-74 dataset_1mb.csv --pattern offload

# Sistema 2 (Arrow Flight Python) - usa tenant_id
python main.py --backend system2 query tenant_desktop_cfiot58 sales
python main.py --backend system2 query tenant_desktop_cfiot58 sales --rows 1000

# Sistema 3 (Arrow Flight Node.js) - usa tenant_id
python main.py --backend system3 query tenant_desktop_cfiot58 sales
```

### Load Test

```bash
# Sistema 1 - 100 requests, 10 concurrentes
python main.py --backend system1 load-test -n 1000 -c 1000 -d dataset_1mb.csv --connectors cc-28-aa-cd-5c-74

python main.py --backend system1 load-test -n 1000 -c 1000 -d dataset_1mb.csv -p stream --connectors cc-28-aa-cd-5c-74

python main.py --backend system1 load-test -n 100 -c 10 -d dataset_1mb.csv -p offload --connectors cc-28-aa-cd-5c-74



# Sistema 2 - con connector específico
python main.py --backend system2 load-test -n 100 -c 100 --connectors tenant_desktop_cfiot58 -d dataset_1mb

python main.py --backend system2 load-test -n 1000 -c 1000 --connectors tenant_desktop_cfiot58 -d dataset_1mb

# Sistema 3 - exportar resultados a JSON
python main.py --backend system3 load-test -n 50 -c 5 -d sales --json results.json
```

# Comparaciones con concurrencia


``` bash
# Sistema 1 - 100 requests, 100 concurrentes
python main.py --backend system1 load-test -n 1000 -c 1000 -d dataset_1mb.csv -p stream --connectors cc-28-aa-cd-5c-74

# Sistema 2 - 100 requests, 100 concurrentes
python main.py --backend system2 load-test -n 100 -c 100 --connectors tenant_desktop_cfiot58 -d dataset_1mb

# Sistema 3 - 100 requests, 100 concurrentes
python main.py --backend system3 load-test -n 100 -c 100 --connectors tenant_desktop_cfiot58 -d dataset_1mb

``` 

### Opciones de Load Test

| Opción | Descripción |
|--------|-------------|
| `-n, --requests` | Total de requests (default: 100) |
| `-c, --concurrency` | Workers concurrentes (default: 10) |
| `-d, --dataset` | Nombre del dataset |
| `--connectors` | Lista de IDs separados por coma |
| `-p, --pattern` | Patrón: sync, stream (default: sync) |
| `-o, --output` | Archivo CSV de métricas |
| `-j, --json` | Exportar resumen a JSON |

## Configuración

Edita `config.yaml` para cambiar URLs y parámetros:

```yaml
backends:
  system1:
    base_url: "http://localhost:8000"
    timeout: 60
  system2:
    flight_uri: "grpc://localhost:8815"
  system3:
    flight_uri: "grpc://localhost:8815"
```

## Métricas

Todas las queries se registran en `metrics.csv` con formato unificado:

- `backend`: sistema evaluado
- `connector_id`: MAC o tenant_id
- `ttfb_sec`: Time to First Byte
- `total_time_sec`: Tiempo total
- `throughput_bytes_sec`: Velocidad de transferencia