# logging_setup.py
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

DEFAULT_LOGFILE = "logs/app.log"

def setup_logging(name: str = "app",
                  level: int = logging.INFO,
                  logfile: Optional[str] = None,
                  console: bool = True) -> logging.Logger:
    """
    Configure root logger and return a named logger.
    Call once at program startup.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # remove existing handlers to avoid duplicates
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = "%(asctime)s [%(levelname)s] %(name)s %(message)s"
    formatter = logging.Formatter(fmt)

    if console:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)
        root.addHandler(ch)

    if logfile:
        # ensure directory exists
        import os
        os.makedirs(os.path.dirname(logfile) or ".", exist_ok=True)
        fh = RotatingFileHandler(logfile, maxBytes=5_000_000, backupCount=3)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        root.addHandler(fh)

    # reduce noisy libraries (optional)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logging.getLogger(name)
