import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(root: Path):
    folder = root / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    file = RotatingFileHandler(folder / "tool.log", maxBytes=5_000_000,
                               backupCount=3, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logger.handlers[:] = [file, console]
