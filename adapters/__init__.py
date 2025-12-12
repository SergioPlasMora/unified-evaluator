"""
Adapters package for unified evaluator.
"""
from .base import IBackendAdapter, QueryResult, QueryPattern, ConnectorInfo
from .rest_sse import RestSSEAdapter
from .arrow_flight import ArrowFlightAdapter

__all__ = [
    "IBackendAdapter",
    "QueryResult",
    "QueryPattern",
    "ConnectorInfo",
    "RestSSEAdapter",
    "ArrowFlightAdapter"
]

