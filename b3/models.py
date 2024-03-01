from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel


class B3Model(BaseModel):
    """Base Renda Facil model."""

    @classmethod
    @property
    def attrs(cls):
        """Return the attributes of the model."""
        return list(cls.__fields__.keys())


class B3Credentials(B3Model):
    client_id: str
    client_secret: str


class B3AuthUrl(B3Model):
    url: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    ext_expires_in: int
    scope: Optional[str]
