"""
Base adapter interface for all backends.
Defines the common contract that all adapters must implement.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Generator, List
from enum import Enum


class QueryPattern(Enum):
    """Patrones de comunicación soportados."""
    SYNC = "sync"           # Patrón A: Request-Response síncrono
    STREAM = "stream"       # Patrón B: SSE o Arrow Flight streaming
    OFFLOAD = "offload"     # Patrón C: Offload a storage (MinIO)


@dataclass
class QueryResult:
    """
    Resultado unificado de una consulta.
    Normaliza métricas de todos los tipos de backend.
    """
    request_id: str
    backend: str
    connector_id: str
    dataset: str
    pattern: str
    status: str  # "success" | "error" | "timeout"
    
    # Datos recibidos
    rows: int = 0
    bytes: int = 0
    
    # Tiempos (todos en segundos)
    t0_sent: float = 0
    ttfb: float = 0          # Time to first byte
    total_time: float = 0    # Tiempo total end-to-end
    
    # Desglose de latencias
    metadata_latency: float = 0    # Tiempo para obtener metadata (Flight)
    transfer_latency: float = 0    # Tiempo de transferencia de datos
    
    # Métricas calculadas
    throughput_bytes_per_sec: float = 0
    
    # Error info
    error: Optional[str] = None
    
    # Timestamps adicionales del servidor (si disponibles)
    server_timestamps: Dict[str, float] = field(default_factory=dict)
    
    def calculate_metrics(self):
        """Calcula métricas derivadas."""
        if self.total_time > 0 and self.bytes > 0:
            self.throughput_bytes_per_sec = self.bytes / self.total_time


@dataclass
class ConnectorInfo:
    """Información de un conector/tenant conectado."""
    id: str
    status: str
    connected_at: Optional[str] = None
    last_ping: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IBackendAdapter(ABC):
    """
    Interfaz común para todos los backends.
    Cada implementación debe soportar al menos health_check y query_sync.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del backend."""
        pass
    
    @property
    @abstractmethod
    def supported_patterns(self) -> List[QueryPattern]:
        """Patrones de query soportados por este adapter."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Verifica si el backend está disponible.
        Returns: True si está healthy, False si no.
        """
        pass
    
    @abstractmethod
    def list_connectors(self) -> List[ConnectorInfo]:
        """
        Lista los conectores/tenants disponibles.
        Returns: Lista de ConnectorInfo.
        """
        pass
    
    @abstractmethod
    def query_sync(
        self, 
        connector_id: str, 
        dataset: str, 
        timeout: int = 60,
        **kwargs
    ) -> QueryResult:
        """
        Consulta síncrona (Patrón A / Arrow Flight do_get).
        Espera a que todos los datos estén disponibles.
        
        Args:
            connector_id: ID del conector/tenant (MAC o tenant_id)
            dataset: Nombre del dataset
            timeout: Timeout en segundos
            
        Returns:
            QueryResult con datos y métricas
        """
        pass
    
    def query_stream(
        self, 
        connector_id: str, 
        dataset: str,
        output_file: Optional[str] = None,
        **kwargs
    ) -> Generator[bytes, None, QueryResult]:
        """
        Consulta streaming (Patrón B / SSE).
        Yield chunks de datos a medida que llegan.
        
        Args:
            connector_id: ID del conector/tenant
            dataset: Nombre del dataset
            output_file: Archivo opcional para guardar datos
            
        Yields:
            Chunks de bytes
            
        Returns:
            QueryResult final con métricas completas
        """
        raise NotImplementedError(f"{self.name} does not support streaming pattern")
    
    def query_offload(
        self, 
        connector_id: str, 
        dataset: str,
        output_file: Optional[str] = None,
        timeout: int = 60,
        **kwargs
    ) -> QueryResult:
        """
        Consulta con offload a storage (Patrón C / MinIO).
        El backend sube los datos a storage y devuelve URL.
        
        Args:
            connector_id: ID del conector/tenant
            dataset: Nombre del dataset
            output_file: Archivo para descargar datos
            timeout: Timeout en segundos
            
        Returns:
            QueryResult con datos y métricas
        """
        raise NotImplementedError(f"{self.name} does not support offload pattern")
