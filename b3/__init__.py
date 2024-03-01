from datetime import date, timedelta
from os import getenv

from config import cfg

from .api import B3
from .enums import MARKET_TYPE

B3_TIME_EDGE: date = lambda: date.today() - timedelta(
    days=558
)  # 18 months ago is the B3 storing edge

B3_client = B3(config=cfg.b3)
