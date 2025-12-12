"""
REST + SSE Adapter for System 1 (luzzi-core-im-enrutador).
Supports Pattern A (sync), Pattern B (SSE stream), and Pattern C (MinIO offload).
"""
import time
import uuid
import requests
from typing import List, Optional, Generator, Dict, Any
import logging

from .base import (
    IBackendAdapter, 
    QueryResult, 
    QueryPattern, 
    ConnectorInfo
)

logger = logging.getLogger(__name__)


class RestSSEAdapter(IBackendAdapter):
    """
    Adaptador para luzzi-core-im-enrutador.
    Protocolos: REST + SSE + WebSocket
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 60,
        poll_interval_ms: int = 500,
        max_poll_attempts: int = 120,
        backend_name: str = "system1"
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._poll_interval = poll_interval_ms / 1000.0
        self._max_poll_attempts = max_poll_attempts
        self._backend_name = backend_name
        self._session = requests.Session()
    
    @property
    def name(self) -> str:
        return self._backend_name
    
    @property
    def supported_patterns(self) -> List[QueryPattern]:
        return [QueryPattern.SYNC, QueryPattern.STREAM, QueryPattern.OFFLOAD]
    
    def health_check(self) -> bool:
        """Verifica si el Enrutador está activo."""
        try:
            response = self._session.get(
                f"{self._base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def list_connectors(self) -> List[ConnectorInfo]:
        """Lista los Conectores activos vía SSE registry."""
        try:
            response = self._session.get(
                f"{self._base_url}/hosts/active",
                timeout=self._timeout
            )
            response.raise_for_status()
            data = response.json()
            
            connectors = []
            for c in data.get("connectors", []):
                connectors.append(ConnectorInfo(
                    id=c.get("mac_address", ""),
                    status=c.get("status", "unknown"),
                    connected_at=c.get("connected_at"),
                    last_ping=c.get("last_ping"),
                    metadata=c
                ))
            return connectors
            
        except Exception as e:
            logger.error(f"Error listing connectors: {e}")
            return []
    
    def query_sync(
        self, 
        connector_id: str, 
        dataset: str, 
        timeout: int = 60,
        **kwargs
    ) -> QueryResult:
        """
        Patrón A: Solicita dataset y espera respuesta síncrona.
        Usa el endpoint /datasets/request-sync.
        """
        request_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        
        result = QueryResult(
            request_id=request_id,
            backend=self._backend_name,
            connector_id=connector_id,
            dataset=dataset,
            pattern=QueryPattern.SYNC.value,
            status="pending",
            t0_sent=t0
        )
        
        try:
            # Llamar endpoint síncrono
            response = self._session.post(
                f"{self._base_url}/datasets/request-sync",
                json={
                    "mac_address": connector_id,
                    "dataset_name": dataset
                },
                timeout=timeout
            )
            
            t4 = time.perf_counter()
            result.total_time = t4 - t0
            result.ttfb = result.total_time  # En sync, TTFB = total time
            
            if response.status_code == 200:
                data = response.json()
                result.status = "success"
                result.request_id = data.get("request_id", request_id)
                
                # Extraer datos y métricas
                if "data" in data:
                    result.bytes = len(data["data"]) if isinstance(data["data"], str) else 0
                if "data_size_bytes" in data:
                    result.bytes = data["data_size_bytes"]
                    
                # Timestamps del servidor
                if "timestamps" in data:
                    result.server_timestamps = data["timestamps"]
                    
            else:
                result.status = "error"
                result.error = f"HTTP {response.status_code}: {response.text[:200]}"
                
        except requests.Timeout:
            result.status = "timeout"
            result.error = f"Timeout after {timeout}s"
            result.total_time = time.perf_counter() - t0
            
        except Exception as e:
            result.status = "error"
            result.error = str(e)
            result.total_time = time.perf_counter() - t0
        
        result.calculate_metrics()
        return result
    
    def query_stream(
        self, 
        connector_id: str, 
        dataset: str,
        output_file: Optional[str] = None,
        **kwargs
    ) -> Generator[bytes, None, QueryResult]:
        """
        Patrón B: Solicita dataset via streaming.
        1. POST /datasets/request-stream para iniciar
        2. GET /datasets/stream/{request_id} para consumir
        """
        t0 = time.perf_counter()
        ttfb = 0
        total_bytes = 0
        chunks_received = 0
        request_id = None
        
        result = QueryResult(
            request_id="pending",
            backend=self._backend_name,
            connector_id=connector_id,
            dataset=dataset,
            pattern=QueryPattern.STREAM.value,
            status="pending",
            t0_sent=t0
        )
        
        output_handle = None
        if output_file:
            output_handle = open(output_file, 'wb')
        
        try:
            # 1. Iniciar request de streaming
            init_response = self._session.post(
                f"{self._base_url}/datasets/request-stream",
                json={
                    "mac_address": connector_id,
                    "dataset_name": dataset
                },
                timeout=30
            )
            init_response.raise_for_status()
            init_data = init_response.json()
            request_id = init_data.get("request_id")
            result.request_id = request_id
            
            # 2. Consumir el stream
            stream_response = self._session.get(
                f"{self._base_url}/datasets/stream/{request_id}",
                stream=True,
                timeout=self._timeout
            )
            stream_response.raise_for_status()
            
            # Procesar stream binario
            for chunk in stream_response.iter_content(chunk_size=65536):
                if chunk:
                    # Registrar TTFB en primer chunk
                    if chunks_received == 0:
                        ttfb = time.perf_counter() - t0
                    
                    chunks_received += 1
                    
                    # Verificar si es marcador de fin
                    if b'---STREAM_COMPLETE---' in chunk:
                        # Extraer datos antes del marcador
                        parts = chunk.split(b'---STREAM_COMPLETE---')
                        if parts[0]:
                            total_bytes += len(parts[0])
                            if output_handle:
                                output_handle.write(parts[0])
                            yield parts[0]
                        break
                    
                    total_bytes += len(chunk)
                    
                    if output_handle:
                        output_handle.write(chunk)
                    
                    yield chunk
            
            result.status = "success"
            
        except Exception as e:
            result.status = "error"
            result.error = str(e)
            logger.error(f"Stream error: {e}")
            
        finally:
            if output_handle:
                output_handle.close()
        
        # Calcular métricas finales
        result.total_time = time.perf_counter() - t0
        result.ttfb = ttfb
        result.bytes = total_bytes
        result.calculate_metrics()
        
        return result
    
    def query_offload(
        self, 
        connector_id: str, 
        dataset: str,
        output_file: Optional[str] = None,
        timeout: int = 60,
        **kwargs
    ) -> QueryResult:
        """
        Patrón C: Solicita dataset con offload a MinIO.
        El Conector sube a MinIO y recibimos URL de descarga.
        """
        request_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        
        result = QueryResult(
            request_id=request_id,
            backend=self._backend_name,
            connector_id=connector_id,
            dataset=dataset,
            pattern=QueryPattern.OFFLOAD.value,
            status="pending",
            t0_sent=t0
        )
        
        try:
            # 1. Iniciar request
            response = self._session.post(
                f"{self._base_url}/datasets/request-offload",
                json={
                    "mac_address": connector_id,
                    "dataset_name": dataset
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            result.request_id = data.get("request_id", request_id)
            
            # 2. Polling hasta obtener download_url
            download_url = None
            for _ in range(self._max_poll_attempts):
                status_response = self._session.get(
                    f"{self._base_url}/datasets/{result.request_id}/status",
                    timeout=10
                )
                status_data = status_response.json()
                
                if status_data.get("status") == "completed":
                    download_url = status_data.get("download_url")
                    result.server_timestamps = status_data.get("timestamps", {})
                    break
                elif status_data.get("status") == "error":
                    result.status = "error"
                    result.error = status_data.get("error", "Unknown error")
                    break
                    
                time.sleep(self._poll_interval)
            
            # 3. Descargar desde MinIO si tenemos URL
            if download_url:
                result.ttfb = time.perf_counter() - t0
                
                download_response = self._session.get(download_url, stream=True)
                download_response.raise_for_status()
                
                content = download_response.content
                result.bytes = len(content)
                
                if output_file:
                    with open(output_file, 'wb') as f:
                        f.write(content)
                
                result.status = "success"
            elif result.status == "pending":
                result.status = "timeout"
                result.error = "Polling timeout waiting for download URL"
                
        except Exception as e:
            result.status = "error"
            result.error = str(e)
        
        result.total_time = time.perf_counter() - t0
        result.calculate_metrics()
        return result
