"""
Unified Load Tester.
Runs concurrent requests against any backend adapter.
"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable
from dataclasses import dataclass

from adapters.base import IBackendAdapter, QueryResult, QueryPattern
from metrics import MetricsCollector, LoadTestMetrics

logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Configuración de load test."""
    total_requests: int = 100
    concurrency: int = 10
    dataset: str = "default"
    connector_ids: List[str] = None  # None = usar todos
    pattern: QueryPattern = QueryPattern.SYNC
    rows: Optional[int] = None
    output_file: Optional[str] = None


class LoadTester:
    """
    Load tester unificado que funciona con cualquier adapter.
    """
    
    def __init__(self, adapter: IBackendAdapter):
        self.adapter = adapter
        self.metrics = MetricsCollector()
    
    def _execute_single_request(
        self,
        connector_id: str,
        dataset: str,
        pattern: QueryPattern,
        rows: Optional[int] = None
    ) -> QueryResult:
        """Ejecuta una request individual."""
        try:
            if pattern == QueryPattern.SYNC:
                return self.adapter.query_sync(
                    connector_id=connector_id,
                    dataset=dataset,
                    rows=rows
                )
            elif pattern == QueryPattern.STREAM:
                # Para stream, consumimos el generator y construimos result manualmente
                t0 = time.perf_counter()
                ttfb = 0
                total_bytes = 0
                chunks = 0
                
                try:
                    gen = self.adapter.query_stream(
                        connector_id=connector_id,
                        dataset=dataset
                    )
                    for chunk in gen:
                        if chunks == 0:
                            ttfb = time.perf_counter() - t0
                        chunks += 1
                        total_bytes += len(chunk)
                    
                    status = "success"
                    error = None
                except Exception as e:
                    status = "error"
                    error = str(e)
                
                total_time = time.perf_counter() - t0
                
                return QueryResult(
                    request_id=f"{connector_id}:{dataset}:{t0}",
                    backend=self.adapter.name,
                    connector_id=connector_id,
                    dataset=dataset,
                    pattern=pattern.value,
                    status=status,
                    bytes=total_bytes,
                    ttfb=ttfb,
                    total_time=total_time,
                    error=error
                )
            elif pattern == QueryPattern.OFFLOAD:
                return self.adapter.query_offload(
                    connector_id=connector_id,
                    dataset=dataset
                )
            else:
                raise ValueError(f"Unsupported pattern: {pattern}")
                
        except Exception as e:
            return QueryResult(
                request_id=f"error-{time.time()}",
                backend=self.adapter.name,
                connector_id=connector_id,
                dataset=dataset,
                pattern=pattern.value,
                status="error",
                error=str(e)
            )
    
    def run(
        self,
        config: LoadTestConfig,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> LoadTestMetrics:
        """
        Ejecuta load test.
        
        Args:
            config: Configuración del test
            progress_callback: Callback(completed, total) para progreso
            
        Returns:
            LoadTestMetrics con resultados agregados
        """
        # Validar pattern soportado
        if config.pattern not in self.adapter.supported_patterns:
            raise ValueError(
                f"Pattern {config.pattern} not supported by {self.adapter.name}. "
                f"Supported: {self.adapter.supported_patterns}"
            )
        
        # Obtener connector IDs
        connector_ids = config.connector_ids
        if not connector_ids:
            connectors = self.adapter.list_connectors()
            connector_ids = [c.id for c in connectors]
            if not connector_ids:
                connector_ids = ["default"]
        
        logger.info(
            f"Starting load test: {config.total_requests} requests, "
            f"{config.concurrency} concurrent, pattern={config.pattern.value}"
        )
        
        results: List[QueryResult] = []
        completed = 0
        
        t_start = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
            futures = []
            
            for i in range(config.total_requests):
                # Round-robin connector selection
                connector_id = connector_ids[i % len(connector_ids)]
                
                future = executor.submit(
                    self._execute_single_request,
                    connector_id,
                    config.dataset,
                    config.pattern,
                    config.rows
                )
                futures.append(future)
            
            # Recolectar resultados
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Request failed: {e}")
                    results.append(QueryResult(
                        request_id=f"error-{time.time()}",
                        backend=self.adapter.name,
                        connector_id="unknown",
                        dataset=config.dataset,
                        pattern=config.pattern.value,
                        status="error",
                        error=str(e)
                    ))
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, config.total_requests)
        
        t_end = time.perf_counter()
        duration = t_end - t_start
        
        # Calcular métricas agregadas
        metrics = MetricsCollector.calculate_load_test_metrics(results, duration)
        
        # Guardar resultados individuales
        self.metrics.add_results(results)
        if config.output_file:
            self.metrics.output_file = config.output_file
        self.metrics.save_to_csv()
        
        logger.info(
            f"Load test complete: {metrics.successful}/{metrics.total_requests} successful, "
            f"{metrics.requests_per_second:.2f} req/s, avg latency {metrics.avg_latency_ms:.2f}ms"
        )
        
        return metrics
