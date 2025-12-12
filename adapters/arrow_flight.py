"""
Arrow Flight Adapter for Systems 2 & 3.
System 2: enrutador-gateway (Python)
System 3: enrutador-gateway-node (Node.js)
Both expose Arrow Flight gRPC interface.
"""
import time
import logging
import requests
from typing import List, Optional, Generator

import pyarrow as pa
import pyarrow.flight as flight

from .base import (
    IBackendAdapter, 
    QueryResult, 
    QueryPattern, 
    ConnectorInfo
)

logger = logging.getLogger(__name__)


class ArrowFlightAdapter(IBackendAdapter):
    """
    Adaptador para enrutador-gateway y enrutador-gateway-node.
    Protocolo: Arrow Flight (gRPC)
    """
    
    # Cache for compiled proto stubs (shared across all instances for system3)
    _proto_stubs = None
    _grpc_channel = None
    _stubs_compiled = False
    
    def __init__(
        self,
        flight_uri: str = "grpc://localhost:8815",
        health_url: str = "http://localhost:8080/health",
        timeout: int = 60,
        backend_name: str = "system2"
    ):
        self._flight_uri = flight_uri
        self._health_url = health_url
        self._timeout = timeout
        self._backend_name = backend_name
        self._client: Optional[flight.FlightClient] = None
    
    @property
    def name(self) -> str:
        return self._backend_name
    
    @property
    def supported_patterns(self) -> List[QueryPattern]:
        return [QueryPattern.SYNC, QueryPattern.STREAM]
    
    def _get_client(self) -> flight.FlightClient:
        """Lazy initialization del cliente Flight."""
        if self._client is None:
            self._client = flight.FlightClient(self._flight_uri)
        return self._client
    
    def health_check(self) -> bool:
        """Verifica conectividad con el Gateway."""
        try:
            # Intentar HTTP health check primero
            response = requests.get(self._health_url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        
        # Fallback: intentar list_flights
        try:
            client = self._get_client()
            list(client.list_flights())
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def list_connectors(self) -> List[ConnectorInfo]:
        """Lista los tenants conectados via Flight list_flights."""
        connectors = []
        try:
            client = self._get_client()
            for flight_info in client.list_flights():
                # Extraer tenant_id del descriptor path
                if flight_info.descriptor.path:
                    tenant_id = flight_info.descriptor.path[0].decode('utf-8')
                    connectors.append(ConnectorInfo(
                        id=tenant_id,
                        status="connected",
                        metadata={
                            "total_records": flight_info.total_records,
                            "total_bytes": flight_info.total_bytes
                        }
                    ))
        except Exception as e:
            logger.error(f"Error listing connectors: {e}")
        
        return connectors
    
    def query_sync(
        self, 
        connector_id: str, 
        dataset: str, 
        timeout: int = 60,
        rows: Optional[int] = None,
        **kwargs
    ) -> QueryResult:
        """
        Arrow Flight: GetFlightInfo + DoGet.
        Lee todos los datos de forma síncrona.
        
        Para system3 (Node.js), usa método alternativo por incompatibilidad de protocolo.
        """
        # System3 usa implementación alternativa
        if self._backend_name == "system3":
            return self._query_sync_raw(connector_id, dataset, timeout, rows)
        
        t0 = time.perf_counter()
        
        result = QueryResult(
            request_id=f"{connector_id}:{dataset}:{t0}",
            backend=self._backend_name,
            connector_id=connector_id,
            dataset=dataset,
            pattern=QueryPattern.SYNC.value,
            status="pending",
            t0_sent=t0
        )
        
        try:
            client = self._get_client()
            
            # 1. GetFlightInfo
            t_meta_start = time.perf_counter()
            
            path_args = [connector_id.encode(), dataset.encode()]
            if rows:
                path_args.append(str(rows).encode())
            
            descriptor = flight.FlightDescriptor.for_path(*path_args)
            info = client.get_flight_info(descriptor)
            
            t_meta_end = time.perf_counter()
            result.metadata_latency = t_meta_end - t_meta_start
            
            if not info.endpoints:
                result.status = "error"
                result.error = "No endpoints returned from GetFlightInfo"
                result.total_time = time.perf_counter() - t0
                return result
            
            # 2. DoGet
            t_transfer_start = time.perf_counter()
            
            endpoint = info.endpoints[0]
            reader = client.do_get(endpoint.ticket)
            
            # Leer todos los datos
            table = reader.read_all()
            
            t_transfer_end = time.perf_counter()
            result.transfer_latency = t_transfer_end - t_transfer_start
            result.ttfb = t_meta_end - t0  # TTFB = tiempo hasta metadata
            
            # Métricas de datos
            result.rows = table.num_rows
            result.bytes = table.nbytes
            result.status = "success"
            
        except flight.FlightError as e:
            result.status = "error"
            result.error = f"Flight error: {e}"
            
        except Exception as e:
            result.status = "error"
            result.error = str(e)
        
        result.total_time = time.perf_counter() - t0
        result.calculate_metrics()
        return result
    
    def _query_sync_raw(
        self, 
        connector_id: str, 
        dataset: str, 
        timeout: int = 60,
        rows: Optional[int] = None
    ) -> QueryResult:
        """
        Método alternativo para system3 (Node.js).
        Usa gRPC directo (como cli-client-node) y parsea IPC chunks con pyarrow.
        
        OPTIMIZADO: Cachea los stubs y reutiliza el canal gRPC.
        """
        import grpc
        from pathlib import Path
        
        t0 = time.perf_counter()
        
        result = QueryResult(
            request_id=f"{connector_id}:{dataset}:{t0}",
            backend=self._backend_name,
            connector_id=connector_id,
            dataset=dataset,
            pattern=QueryPattern.SYNC.value,
            status="pending",
            t0_sent=t0
        )
        
        try:
            # Inicializar stubs una sola vez (thread-safe con caching a nivel de clase)
            if not ArrowFlightAdapter._stubs_compiled:
                self._compile_proto_stubs()
            
            # Obtener stubs desde cache
            flight_pb2 = ArrowFlightAdapter._proto_stubs['pb2']
            flight_pb2_grpc = ArrowFlightAdapter._proto_stubs['pb2_grpc']
            
            # Reutilizar o crear canal gRPC
            uri = self._flight_uri.replace("grpc://", "")
            if ArrowFlightAdapter._grpc_channel is None:
                ArrowFlightAdapter._grpc_channel = grpc.insecure_channel(uri, options=[
                    ('grpc.max_receive_message_length', 200 * 1024 * 1024),
                ])
            
            stub = flight_pb2_grpc.FlightServiceStub(ArrowFlightAdapter._grpc_channel)
            
            # 1. GetFlightInfo
            path = [connector_id.encode(), dataset.encode()]
            if rows:
                path.append(str(rows).encode())
            
            descriptor = flight_pb2.FlightDescriptor(
                type=flight_pb2.FlightDescriptor.PATH,
                path=path
            )
            
            info = stub.GetFlightInfo(descriptor, timeout=timeout)
            result.ttfb = time.perf_counter() - t0
            
            if not info.endpoint:
                result.status = "error"
                result.error = "No endpoints returned"
                result.total_time = time.perf_counter() - t0
                return result
            
            # 2. DoGet - recibir chunks y parsear como IPC
            ticket = info.endpoint[0].ticket
            
            chunks = []
            for flight_data in stub.DoGet(flight_pb2.Ticket(ticket=ticket.ticket), timeout=timeout):
                if flight_data.data_body and len(flight_data.data_body) > 0:
                    chunks.append(flight_data.data_body)
            
            # Parsear chunks IPC
            if not chunks:
                result.status = "error"
                result.error = "No data received"
                result.total_time = time.perf_counter() - t0
                return result
            
            total_rows = 0
            total_bytes = 0
            
            for chunk in chunks:
                buffer = pa.py_buffer(chunk)
                reader = pa.ipc.open_stream(buffer)
                table = reader.read_all()
                total_rows += table.num_rows
                total_bytes += len(chunk)
            
            result.rows = total_rows
            result.bytes = total_bytes
            result.status = "success"
                
        except Exception as e:
            result.status = "error"
            result.error = str(e)
            logger.error(f"System3 query error: {e}")
        
        result.total_time = time.perf_counter() - t0
        result.calculate_metrics()
        return result
    
    def _compile_proto_stubs(self):
        """Compila los stubs de proto una sola vez y los cachea."""
        import sys
        import tempfile
        import os
        from pathlib import Path
        from grpc_tools import protoc
        
        # Encontrar el proto de Flight
        proto_paths = [
            Path(__file__).parent.parent.parent / "enrutador-gateway-node" / "proto" / "Flight.proto",
            Path(__file__).parent.parent / "proto" / "Flight.proto",
        ]
        
        proto_path = None
        for p in proto_paths:
            if p.exists():
                proto_path = p
                break
        
        if not proto_path:
            raise FileNotFoundError("Flight.proto not found. System3 requires the proto file.")
        
        proto_dir = proto_path.parent
        
        # Crear directorio persistente para los stubs
        stubs_dir = Path(__file__).parent / ".grpc_stubs"
        stubs_dir.mkdir(exist_ok=True)
        
        # Compilar proto solo si no existe
        pb2_file = stubs_dir / "Flight_pb2.py"
        if not pb2_file.exists():
            protoc.main([
                'grpc_tools.protoc',
                f'-I{proto_dir}',
                f'--python_out={stubs_dir}',
                f'--grpc_python_out={stubs_dir}',
                str(proto_path)
            ])
        
        # Importar los módulos generados
        if str(stubs_dir) not in sys.path:
            sys.path.insert(0, str(stubs_dir))
        
        import Flight_pb2 as flight_pb2
        import Flight_pb2_grpc as flight_pb2_grpc
        
        # Cachear
        ArrowFlightAdapter._proto_stubs = {
            'pb2': flight_pb2,
            'pb2_grpc': flight_pb2_grpc
        }
        ArrowFlightAdapter._stubs_compiled = True
        logger.info("Proto stubs compiled and cached for system3")
    
    def query_stream(
        self, 
        connector_id: str, 
        dataset: str,
        output_file: Optional[str] = None,
        rows: Optional[int] = None,
        **kwargs
    ) -> Generator[bytes, None, QueryResult]:
        """
        Arrow Flight: DoGet con streaming.
        Yield batches Arrow IPC a medida que llegan.
        """
        t0 = time.perf_counter()
        ttfb = 0
        total_rows = 0
        total_bytes = 0
        chunks = 0
        
        result = QueryResult(
            request_id=f"{connector_id}:{dataset}:{t0}",
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
            client = self._get_client()
            
            # 1. GetFlightInfo
            t_meta_start = time.perf_counter()
            
            path_args = [connector_id.encode(), dataset.encode()]
            if rows:
                path_args.append(str(rows).encode())
            
            descriptor = flight.FlightDescriptor.for_path(*path_args)
            info = client.get_flight_info(descriptor)
            
            result.metadata_latency = time.perf_counter() - t_meta_start
            
            if not info.endpoints:
                result.status = "error"
                result.error = "No endpoints returned"
                return result
            
            # 2. DoGet streaming
            endpoint = info.endpoints[0]
            reader = client.do_get(endpoint.ticket)
            
            # Stream batches
            for chunk in reader:
                if chunks == 0:
                    ttfb = time.perf_counter() - t0
                
                chunks += 1
                batch = chunk.data
                total_rows += batch.num_rows
                
                # Serializar a IPC para yield
                sink = pa.BufferOutputStream()
                with pa.ipc.new_stream(sink, batch.schema) as writer:
                    writer.write_batch(batch)
                
                ipc_bytes = sink.getvalue().to_pybytes()
                total_bytes += len(ipc_bytes)
                
                if output_handle:
                    output_handle.write(ipc_bytes)
                
                yield ipc_bytes
            
            result.status = "success"
            
        except Exception as e:
            result.status = "error"
            result.error = str(e)
            
        finally:
            if output_handle:
                output_handle.close()
        
        result.total_time = time.perf_counter() - t0
        result.ttfb = ttfb
        result.rows = total_rows
        result.bytes = total_bytes
        result.calculate_metrics()
        
        return result
