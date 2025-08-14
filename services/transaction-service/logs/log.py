import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger: logging.Logger = logging.getLogger("transaction_service")

__all__ = ["logger"]
