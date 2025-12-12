#!/usr/bin/env python3
"""
Unified Evaluator - CLI principal.
Cliente unificado para evaluar los 3 sistemas backend.

Uso:
    python main.py --backend system1 query MAC dataset.csv
    python main.py --backend system2 query tenant_id dataset
    python main.py --backend system3 load-test --requests 100 --concurrency 10
"""
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

import yaml

from adapters import RestSSEAdapter, ArrowFlightAdapter, IBackendAdapter, QueryPattern
from metrics import MetricsCollector, LoadTestMetrics
from load_tester import LoadTester, LoadTestConfig
from logger import setup_logger

# Rich para output bonito
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def load_config(config_path: str = "config.yaml") -> dict:
    """Carga configuración desde YAML."""
    path = Path(config_path)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def create_adapter(backend_name: str, config: dict) -> IBackendAdapter:
    """Crea el adapter apropiado para el backend."""
    backends = config.get("backends", {})
    
    if backend_name not in backends:
        available = list(backends.keys())
        raise ValueError(f"Backend '{backend_name}' not found. Available: {available}")
    
    backend_config = backends[backend_name]
    adapter_type = backend_config.get("type")
    
    if adapter_type == "rest_sse":
        return RestSSEAdapter(
            base_url=backend_config.get("base_url", "http://localhost:8000"),
            timeout=backend_config.get("timeout", 60),
            poll_interval_ms=backend_config.get("poll_interval_ms", 500),
            max_poll_attempts=backend_config.get("max_poll_attempts", 120),
            backend_name=backend_name
        )
    elif adapter_type == "arrow_flight":
        return ArrowFlightAdapter(
            flight_uri=backend_config.get("flight_uri", "grpc://localhost:8815"),
            health_url=backend_config.get("health_url", "http://localhost:8080/health"),
            timeout=backend_config.get("timeout", 60),
            backend_name=backend_name
        )
    else:
        raise ValueError(f"Unknown adapter type: {adapter_type}")


def print_result(result, console=None):
    """Imprime resultado de query."""
    if RICH_AVAILABLE and console:
        if result.status == "success":
            table = Table(title="✅ Query Result", show_header=False, box=box.SIMPLE)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Backend", result.backend)
            table.add_row("Connector", result.connector_id)
            table.add_row("Dataset", result.dataset)
            table.add_row("Pattern", result.pattern)
            table.add_row("Status", f"[green]{result.status}[/green]")
            table.add_row("Rows", f"{result.rows:,}")
            table.add_row("Bytes", f"{result.bytes:,}")
            table.add_row("TTFB", f"{result.ttfb*1000:.2f} ms")
            table.add_row("Total Time", f"{result.total_time*1000:.2f} ms")
            table.add_row("Throughput", f"{result.throughput_bytes_per_sec/1024/1024:.2f} MB/s")
            
            console.print(table)
        else:
            console.print(Panel(
                f"[red]Error: {result.error}[/red]",
                title="❌ Query Failed"
            ))
    else:
        print(f"\n{'='*50}")
        print(f"Backend:    {result.backend}")
        print(f"Connector:  {result.connector_id}")
        print(f"Dataset:    {result.dataset}")
        print(f"Status:     {result.status}")
        if result.status == "success":
            print(f"Rows:       {result.rows:,}")
            print(f"Bytes:      {result.bytes:,}")
            print(f"TTFB:       {result.ttfb*1000:.2f} ms")
            print(f"Total Time: {result.total_time*1000:.2f} ms")
        else:
            print(f"Error:      {result.error}")
        print('='*50)


def print_load_test_results(metrics: LoadTestMetrics, console=None):
    """Imprime resultados de load test."""
    if RICH_AVAILABLE and console:
        console.print("\n[bold]Load Test Results[/bold]")
        
        # Tabla resumen
        table = Table(title="Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Backend", metrics.backend)
        table.add_row("Pattern", metrics.pattern)
        table.add_row("Duration", f"{metrics.duration_seconds:.2f} s")
        table.add_row("Total Requests", str(metrics.total_requests))
        table.add_row("Successful", f"[green]{metrics.successful}[/green]")
        table.add_row("Failed", f"[red]{metrics.failed}[/red]")
        table.add_row("Throughput", f"{metrics.requests_per_second:.2f} req/s")
        table.add_row("Data Transferred", f"{metrics.total_bytes/1024/1024:.2f} MB")
        
        console.print(table)
        
        # Tabla latencias
        lat_table = Table(title="Latency Statistics (ms)", box=box.ROUNDED)
        lat_table.add_column("Statistic", style="yellow")
        lat_table.add_column("Time", style="bold white")
        
        lat_table.add_row("Average", f"{metrics.avg_latency_ms:.2f}")
        lat_table.add_row("Min", f"{metrics.min_latency_ms:.2f}")
        lat_table.add_row("Max", f"{metrics.max_latency_ms:.2f}")
        lat_table.add_row("P50", f"{metrics.p50_latency_ms:.2f}")
        lat_table.add_row("P95", f"{metrics.p95_latency_ms:.2f}")
        lat_table.add_row("P99", f"{metrics.p99_latency_ms:.2f}")
        lat_table.add_row("Avg TTFB", f"{metrics.avg_ttfb_ms:.2f}")
        
        console.print(lat_table)
    else:
        print(f"\n{'='*50}")
        print("LOAD TEST RESULTS")
        print(f"{'='*50}")
        print(f"Backend:      {metrics.backend}")
        print(f"Pattern:      {metrics.pattern}")
        print(f"Duration:     {metrics.duration_seconds:.2f} s")
        print(f"Requests:     {metrics.total_requests}")
        print(f"Successful:   {metrics.successful}")
        print(f"Failed:       {metrics.failed}")
        print(f"Req/s:        {metrics.requests_per_second:.2f}")
        print(f"\nLatencies (ms):")
        print(f"  Average:    {metrics.avg_latency_ms:.2f}")
        print(f"  P95:        {metrics.p95_latency_ms:.2f}")
        print(f"  P99:        {metrics.p99_latency_ms:.2f}")
        print('='*50)


def consume_stream_query(adapter, connector_id, dataset, output_file=None):
    """
    Helper para consumir stream query y retornar resultado.
    El Generator de query_stream tiene un bug con return, así que manejamos
    el resultado de forma diferente.
    """
    import time
    from adapters.base import QueryResult, QueryPattern
    
    t0 = time.perf_counter()
    ttfb = 0
    total_bytes = 0
    chunks = 0
    
    output_handle = None
    if output_file:
        output_handle = open(output_file, 'wb')
    
    try:
        gen = adapter.query_stream(
            connector_id=connector_id,
            dataset=dataset,
            output_file=None  # Manejamos output aquí
        )
        
        for chunk in gen:
            if chunks == 0:
                ttfb = time.perf_counter() - t0
            chunks += 1
            total_bytes += len(chunk)
            
            if output_handle:
                output_handle.write(chunk)
        
        status = "success"
        error = None
        
    except Exception as e:
        status = "error"
        error = str(e)
    
    finally:
        if output_handle:
            output_handle.close()
    
    total_time = time.perf_counter() - t0
    
    result = QueryResult(
        request_id=f"{connector_id}:{dataset}:{t0}",
        backend=adapter.name,
        connector_id=connector_id,
        dataset=dataset,
        pattern=QueryPattern.STREAM.value,
        status=status,
        bytes=total_bytes,
        ttfb=ttfb,
        total_time=total_time,
        error=error
    )
    result.calculate_metrics()
    return result


# ============== COMMANDS ==============

def cmd_health(args, adapter: IBackendAdapter, console):
    """Verifica salud del backend."""
    healthy = adapter.health_check()
    
    if RICH_AVAILABLE and console:
        if healthy:
            console.print(f"[green]✓[/green] {args.backend} is healthy")
        else:
            console.print(f"[red]✗[/red] {args.backend} is not responding")
    else:
        status = "healthy" if healthy else "unhealthy"
        print(f"{args.backend}: {status}")
    
    return 0 if healthy else 1


def cmd_list(args, adapter: IBackendAdapter, console):
    """Lista conectores disponibles."""
    connectors = adapter.list_connectors()
    
    if RICH_AVAILABLE and console:
        if not connectors:
            console.print("[yellow]No connectors found[/yellow]")
            return
        
        table = Table(title=f"Connectors ({len(connectors)})")
        table.add_column("ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Connected At")
        
        for c in connectors:
            table.add_row(c.id, c.status, c.connected_at or "-")
        
        console.print(table)
    else:
        print(f"\nConnectors: {len(connectors)}")
        for c in connectors:
            print(f"  - {c.id}: {c.status}")


def cmd_query(args, adapter: IBackendAdapter, metrics: MetricsCollector, console, logger):
    """Ejecuta una query individual."""
    pattern = QueryPattern[args.pattern.upper()]
    
    logger.info(f"Query: {args.connector}/{args.dataset} via {pattern.value}")
    
    if pattern == QueryPattern.SYNC:
        result = adapter.query_sync(
            connector_id=args.connector,
            dataset=args.dataset,
            timeout=args.timeout,
            rows=getattr(args, 'rows', None)
        )
    elif pattern == QueryPattern.STREAM:
        # Consumir stream y obtener resultado
        result = consume_stream_query(
            adapter, args.connector, args.dataset, 
            getattr(args, 'output', None)
        )
    elif pattern == QueryPattern.OFFLOAD:
        result = adapter.query_offload(
            connector_id=args.connector,
            dataset=args.dataset,
            output_file=getattr(args, 'output', None),
            timeout=args.timeout
        )
    else:
        raise ValueError(f"Unknown pattern: {pattern}")
    
    # Guardar métricas
    metrics.add_result(result)
    metrics.save_to_csv()
    
    # Mostrar resultado
    print_result(result, console)


def cmd_load_test(args, adapter: IBackendAdapter, console, logger):
    """Ejecuta load test."""
    pattern = QueryPattern[args.pattern.upper()]
    
    config = LoadTestConfig(
        total_requests=args.requests,
        concurrency=args.concurrency,
        dataset=args.dataset,
        connector_ids=args.connectors.split(",") if args.connectors else None,
        pattern=pattern,
        rows=getattr(args, 'rows', None),
        output_file=args.output or "metrics.csv"
    )
    
    tester = LoadTester(adapter)
    
    # Progress callback
    def progress(completed, total):
        if RICH_AVAILABLE:
            print(f"\r  Progress: {completed}/{total}", end="", flush=True)
    
    logger.info(f"Starting load test: {config.total_requests} requests, {config.concurrency} concurrent")
    
    metrics = tester.run(config, progress_callback=progress)
    
    print()  # New line after progress
    print_load_test_results(metrics, console)
    
    # Exportar JSON si se pide
    if args.json:
        data = {
            "backend": metrics.backend,
            "pattern": metrics.pattern,
            "summary": {
                "duration_s": metrics.duration_seconds,
                "requests": metrics.total_requests,
                "successful": metrics.successful,
                "failed": metrics.failed,
                "requests_per_second": metrics.requests_per_second
            },
            "latency_ms": {
                "avg": metrics.avg_latency_ms,
                "min": metrics.min_latency_ms,
                "max": metrics.max_latency_ms,
                "p50": metrics.p50_latency_ms,
                "p95": metrics.p95_latency_ms,
                "p99": metrics.p99_latency_ms,
                "avg_ttfb": metrics.avg_ttfb_ms
            },
            "data": {
                "total_bytes": metrics.total_bytes,
                "total_rows": metrics.total_rows,
                "bytes_per_second": metrics.bytes_per_second
            }
        }
        with open(args.json, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Results exported to {args.json}")


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Unified Evaluator - Test all 3 backend systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --backend system1 health
  python main.py --backend system1 list
  python main.py --backend system1 query MAC dataset.csv
  python main.py --backend system2 query tenant_id dataset --pattern sync
  python main.py --backend system3 load-test --requests 100 --concurrency 10
        """
    )
    
    parser.add_argument(
        "--backend", "-b",
        required=True,
        choices=["system1", "system2", "system3"],
        help="Backend to test (system1=REST/SSE, system2/3=Arrow Flight)"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Health command
    subparsers.add_parser("health", help="Check backend health")
    
    # List command
    subparsers.add_parser("list", help="List available connectors")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Execute a single query")
    query_parser.add_argument("connector", help="Connector/tenant ID")
    query_parser.add_argument("dataset", help="Dataset name")
    query_parser.add_argument(
        "--pattern", "-p",
        default="sync",
        choices=["sync", "stream", "offload"],
        help="Query pattern (default: sync)"
    )
    query_parser.add_argument("--timeout", "-t", type=int, default=60, help="Timeout in seconds")
    query_parser.add_argument("--rows", "-r", type=int, help="Number of rows (optional)")
    query_parser.add_argument("--output", "-o", help="Output file for streaming/offload")
    
    # Load-test command
    load_parser = subparsers.add_parser("load-test", help="Run load test")
    load_parser.add_argument("--requests", "-n", type=int, default=100, help="Total requests")
    load_parser.add_argument("--concurrency", "-c", type=int, default=10, help="Concurrent workers")
    load_parser.add_argument("--dataset", "-d", default="default", help="Dataset name")
    load_parser.add_argument("--connectors", help="Comma-separated connector IDs")
    load_parser.add_argument(
        "--pattern", "-p",
        default="sync",
        choices=["sync", "stream"],
        help="Query pattern (default: sync)"
    )
    load_parser.add_argument("--rows", "-r", type=int, help="Rows per request")
    load_parser.add_argument("--output", "-o", default="metrics.csv", help="Output CSV file")
    load_parser.add_argument("--json", "-j", help="Export results to JSON file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Setup
    config = load_config(args.config)
    logging_config = config.get("logging", {})
    logger = setup_logger(
        level=logging_config.get("level", "INFO"),
        format_type=logging_config.get("format", "text")
    )
    
    console = Console() if RICH_AVAILABLE else None
    
    # Print header
    if RICH_AVAILABLE and console:
        console.print(Panel.fit(
            f"[bold cyan]Unified Evaluator[/bold cyan]\n"
            f"[yellow]Backend: {args.backend}[/yellow]",
            border_style="blue"
        ))
    
    try:
        adapter = create_adapter(args.backend, config)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    metrics_config = config.get("metrics", {})
    metrics = MetricsCollector(
        output_file=metrics_config.get("output_file", "metrics.csv")
    )
    
    # Execute command
    try:
        if args.command == "health":
            exit_code = cmd_health(args, adapter, console)
            sys.exit(exit_code)
        elif args.command == "list":
            cmd_list(args, adapter, console)
        elif args.command == "query":
            cmd_query(args, adapter, metrics, console, logger)
        elif args.command == "load-test":
            cmd_load_test(args, adapter, console, logger)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        if RICH_AVAILABLE and console:
            console.print(f"[red]Error:[/red] {e}")
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
