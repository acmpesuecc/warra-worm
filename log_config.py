# log_config.py
import logging
import sys

LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
}

def setup_logging(level='INFO'):
    """Configures the root logger."""
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    
    # Configure the root logger
    logging.basicConfig(level=log_level, format=log_format, stream=sys.stdout)
    
    # Silence overly verbose libraries (like paramiko) if needed
    logging.getLogger("paramiko").setLevel(logging.WARNING) 
    
    logging.info(f"Logging configured at level: {level.upper()}")