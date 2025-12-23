import logging
import json
from datetime import datetime
import sys

class JSONFormatter(logging.Formatter):
    """
    Structured JSON formatter for machine-readable logs.
    Makes debugging and monitoring 10x easier.
    """
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'run_id'):
            log_data['run_id'] = record.run_id
        if hasattr(record, 'game_count'):
            log_data['game_count'] = record.game_count
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'html_size_kb'):
            log_data['html_size_kb'] = record.html_size_kb
            
        return json.dumps(log_data)

def setup_logger(name):
    """
    Create a logger with JSON formatting.
    Usage: logger = setup_logger(__name__)
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    
    return logger
