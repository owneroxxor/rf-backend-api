from os import environ
from pathlib import Path

from .config import AppConfig

cfg = AppConfig(Path(__file__).parent / "config.yml", environ.get("RF_ENV", "DEV"))
