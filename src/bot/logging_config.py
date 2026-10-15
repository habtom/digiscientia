# logging_config.py
import logging
from threading import Lock

class LogBuffer:
    buffer = []
    lock = Lock()

class StreamlitLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        with LogBuffer.lock:
            LogBuffer.buffer.append(log_entry)

def setup_logger():
    logger = logging.getLogger('DigiScientiaBot')
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = StreamlitLogHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

__all__ = ['setup_logger', 'LogBuffer']