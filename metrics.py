"""
Unified Metrics Collector.
Collects and exports metrics from all backends in a consistent format.
"""
import csv
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any

from adapters.base import QueryResult


@dataclass
class LoadTestMetrics:
    """Métricas agregadas de un load test."""
    backend: str
    pattern: str
    duration_seconds: float
    total_requests: int
    successful: int
    failed: int
    
    # Datos
    total_rows: int = 0
    total_bytes: int = 0
    
    # Latencias (en ms)
    avg_latency_ms: float = 0
    min_latency_ms: float = 0
    max_latency_ms: float = 0
    p50_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    
    # Throughput
    requests_per_second: float = 0
    bytes_per_second: float = 0
    
    # TTFB
    avg_ttfb_ms: float = 0


class MetricsCollector:
    """
    Recolector de métricas unificado.
    Soporta tanto queries individuales como load tests.
    """
    
    def __init__(self, output_file: str = "metrics.csv"):
        self.output_file = output_file
        self.entries: List[QueryResult] = []
    
    def add_result(self, result: QueryResult):
        """Agrega un resultado de query."""
        self.entries.append(result)
    
    def add_results(self, results: List[QueryResult]):
        """Agrega múltiples resultados."""
        self.entries.extend(results)
    
    def save_to_csv(self, append: bool = True):
        """Guarda métricas a CSV."""
        if not self.entries:
            return
        
        file_exists = os.path.exists(self.output_file)
        mode = 'a' if append and file_exists else 'w'
        
        with open(self.output_file, mode, newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header si es archivo nuevo
            if mode == 'w' or not file_exists:
                writer.writerow([
                    "timestamp", "backend", "connector_id", "dataset", "pattern",
                    "status", "rows", "bytes", "ttfb_sec", "total_time_sec",
                    "metadata_latency_sec", "transfer_latency_sec",
                    "throughput_bytes_sec", "error"
                ])
            
            for entry in self.entries:
                writer.writerow([
                    datetime.now().isoformat(),
                    entry.backend,
                    entry.connector_id,
                    entry.dataset,
                    entry.pattern,
                    entry.status,
                    entry.rows,
                    entry.bytes,
                    f"{entry.ttfb:.6f}",
                    f"{entry.total_time:.6f}",
                    f"{entry.metadata_latency:.6f}",
                    f"{entry.transfer_latency:.6f}",
                    f"{entry.throughput_bytes_per_sec:.2f}",
                    entry.error or ""
                ])
        
        # Limpiar entries después de guardar
        self.entries = []
    
    def get_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de métricas."""
        if not self.entries:
            return {"count": 0}
        
        successful = [e for e in self.entries if e.status == "success"]
        
        if not successful:
            return {
                "count": len(self.entries),
                "successful": 0,
                "failed": len(self.entries)
            }
        
        ttfbs = [e.ttfb for e in successful]
        total_times = [e.total_time for e in successful]
        throughputs = [e.throughput_bytes_per_sec for e in successful if e.throughput_bytes_per_sec > 0]
        
        return {
            "count": len(self.entries),
            "successful": len(successful),
            "failed": len(self.entries) - len(successful),
            "avg_ttfb_seconds": statistics.mean(ttfbs),
            "min_ttfb_seconds": min(ttfbs),
            "max_ttfb_seconds": max(ttfbs),
            "avg_total_time_seconds": statistics.mean(total_times),
            "avg_throughput_bytes_per_sec": statistics.mean(throughputs) if throughputs else 0,
            "total_bytes": sum(e.bytes for e in successful),
            "total_rows": sum(e.rows for e in successful)
        }
    
    @staticmethod
    def calculate_load_test_metrics(
        results: List[QueryResult],
        duration_seconds: float
    ) -> LoadTestMetrics:
        """Calcula métricas agregadas de un load test."""
        if not results:
            return LoadTestMetrics(
                backend="unknown",
                pattern="unknown",
                duration_seconds=duration_seconds,
                total_requests=0,
                successful=0,
                failed=0
            )
        
        backend = results[0].backend
        pattern = results[0].pattern
        
        successful = [r for r in results if r.status == "success"]
        failed = len(results) - len(successful)
        
        # Latencias en ms
        latencies_ms = [r.total_time * 1000 for r in successful] if successful else [0]
        ttfbs_ms = [r.ttfb * 1000 for r in successful] if successful else [0]
        
        # Percentiles
        sorted_latencies = sorted(latencies_ms)
        
        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f]) if f != c else data[f]
        
        metrics = LoadTestMetrics(
            backend=backend,
            pattern=pattern,
            duration_seconds=duration_seconds,
            total_requests=len(results),
            successful=len(successful),
            failed=failed,
            total_rows=sum(r.rows for r in successful),
            total_bytes=sum(r.bytes for r in successful),
            avg_latency_ms=statistics.mean(latencies_ms) if latencies_ms else 0,
            min_latency_ms=min(latencies_ms) if latencies_ms else 0,
            max_latency_ms=max(latencies_ms) if latencies_ms else 0,
            p50_latency_ms=percentile(sorted_latencies, 50),
            p95_latency_ms=percentile(sorted_latencies, 95),
            p99_latency_ms=percentile(sorted_latencies, 99),
            requests_per_second=len(results) / duration_seconds if duration_seconds > 0 else 0,
            bytes_per_second=sum(r.bytes for r in successful) / duration_seconds if duration_seconds > 0 else 0,
            avg_ttfb_ms=statistics.mean(ttfbs_ms) if ttfbs_ms else 0
        )
        
        return metrics
    
    def clear(self):
        """Limpia las entradas."""
        self.entries = []
