"""
Logging configuration for unified evaluator.
"""
import logging
import sys
from typing import Optional


def setup_logger(
    level: str = "INFO",
    format_type: str = "text"
) -> logging.Logger:
    """
    Configura el logger principal.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        format_type: "text" o "json"
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger("unified-evaluator")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Limpiar handlers existentes
    logger.handlers = []
    
    # Handler para stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    if format_type == "json":
        import json
        
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "module": record.module
                }
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_data)
        
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
