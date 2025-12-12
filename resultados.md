# Resultados

## System1

```bash
python main.py --backend system1 load-test -n 100 -c 100 -d dataset_1mb.csv -p stream --connectors 10-51-07-96-d5-49
╭───────────────────╮
│ Unified Evaluator │
│ Backend: system1  │
╰───────────────────╯
2025-12-12 11:52:25,061 - unified-evaluator - INFO - Starting load test: 100 requests, 100 concurrent
  Progress: 100/100

Load Test Results
             Summary
╭──────────────────┬─────────────╮
│ Metric           │ Value       │
├──────────────────┼─────────────┤
│ Backend          │ system1     │
│ Pattern          │ stream      │
│ Duration         │ 3.74 s      │
│ Total Requests   │ 100         │
│ Successful       │ 100         │
│ Failed           │ 0           │
│ Throughput       │ 26.76 req/s │
│ Data Transferred │ 100.62 MB   │
╰──────────────────┴─────────────╯
Latency Statistics (ms)
╭───────────┬─────────╮
│ Statistic │ Time    │
├───────────┼─────────┤
│ Average   │ 2592.80 │
│ Min       │ 881.57  │
│ Max       │ 3464.35 │
│ P50       │ 2887.92 │
│ P95       │ 3435.92 │
│ P99       │ 3459.59 │
│ Avg TTFB  │ 2088.10 │
╰───────────┴─────────╯
```


## System2

```bash

(venv) C:\Users\sergi\OneDrive\Documentos\GitHub\unified-evaluator>python main.py --backend system2 load-test -n 100 -c 100 --connectors tenant_sergio -d dataset_1mb
╭───────────────────╮
│ Unified Evaluator │
│ Backend: system2  │
╰───────────────────╯
2025-12-12 13:00:04,377 - unified-evaluator - INFO - Starting load test: 100 requests, 100 concurrent
  Progress: 100/100

Load Test Results
             Summary
╭──────────────────┬─────────────╮
│ Metric           │ Value       │
├──────────────────┼─────────────┤
│ Backend          │ system2     │
│ Pattern          │ sync        │
│ Duration         │ 4.78 s      │
│ Total Requests   │ 100         │
│ Successful       │ 100         │
│ Failed           │ 0           │
│ Throughput       │ 20.91 req/s │
│ Data Transferred │ 89.58 MB    │
╰──────────────────┴─────────────╯
Latency Statistics (ms)
╭───────────┬─────────╮
│ Statistic │ Time    │
├───────────┼─────────┤
│ Average   │ 4120.09 │
│ Min       │ 4018.73 │
│ Max       │ 4766.04 │
│ P50       │ 4054.07 │
│ P95       │ 4718.40 │
│ P99       │ 4762.02 │
│ Avg TTFB  │ 350.76  │
╰───────────┴─────────╯

```

## System3

``` bash
python main.py --backend system3 load-test -n 100 -c 100 --connectors tenant_sergio -d dataset_1mb
╭───────────────────╮
│ Unified Evaluator │
│ Backend: system3  │
╰───────────────────╯
2025-12-12 12:57:41,276 - unified-evaluator - INFO - Starting load test: 100 requests, 100 concurrent
  Progress: 100/100

Load Test Results
             Summary
╭──────────────────┬─────────────╮
│ Metric           │ Value       │
├──────────────────┼─────────────┤
│ Backend          │ system3     │
│ Pattern          │ sync        │
│ Duration         │ 1.69 s      │
│ Total Requests   │ 100         │
│ Successful       │ 100         │
│ Failed           │ 0           │
│ Throughput       │ 59.10 req/s │
│ Data Transferred │ 89.83 MB    │
╰──────────────────┴─────────────╯
Latency Statistics (ms)
╭───────────┬─────────╮
│ Statistic │ Time    │
├───────────┼─────────┤
│ Average   │ 1059.05 │
│ Min       │ 710.52  │
│ Max       │ 1439.37 │
│ P50       │ 1048.66 │
│ P95       │ 1431.83 │
│ P99       │ 1438.71 │
│ Avg TTFB  │ 476.76  │
╰───────────┴─────────╯
```