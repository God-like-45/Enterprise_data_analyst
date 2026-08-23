#What it does: Sets up a standardized logger. When an agent fails, this is how we will know why.
import logging
import sys
from app.config.settings import settings

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Avoid duplicate logs if instantiated multiple times
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(settings.log_level.upper())
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger