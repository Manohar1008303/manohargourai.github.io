import logging
import os

def get_logger(name: str, log_level=logging.INFO):
    """
    Returns a configured logger instance.

    Parameters
    ----------
    name : str
        Name of the logger (usually __name__ from the caller module).
    log_level : int
        Logging level (INFO by default).

    Returns
    -------
    logger : logging.Logger
        Configured logger object.
    """

    # Create logs folder if not exists
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Prevent adding multiple handlers to same logger
    if logger.hasHandlers():
        return logger

    # Log format
    formatter = logging.Formatter(
        fmt="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler("logs/clo_engine.log", mode="a")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
