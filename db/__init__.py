from pydantic import config

from config import cfg

from .firebase import FirebaseDB

DB_client = FirebaseDB(
    base_url=cfg.firebase.base_url,
    auth_token=cfg.firebase.auth_token,
)
