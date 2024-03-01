from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel


class RFModel(BaseModel):
    """Base Renda Facil model."""

    @classmethod
    @property
    def attrs(cls):
        """Return the attributes of the model."""
        return list(cls.__fields__.keys())


class Message(RFModel):
    msg: str

class UnauthorizedMessage(Message):
    msg: str = 'Unauthorized to access B3 API on participants\' behalf'

class Movement(RFModel):
    ...


class EquitiesMovement(Movement):
    reference_date: date
    product_category: str
    product_type_name: str
    movement_type: str
    operation_type: str
    ticker_symbol: str
    corporation_name: str
    participant_name: str
    participant_document_number: str
    equities_quantity: int
    unit_price: str
    operation_value: str


class Movements(RFModel):
    document: str
    market_type: str
    year: str
    month: str
    day: str
    movements: List[Movement]

    @property
    def path(self):
        return f"{self.document}/{self.market_type}/{self.year}/{self.month.zfill(2)}/{self.day.zfill(2)}"


class MovementsGrouped(RFModel):
    document: str
    market_type: str
    movements: Dict[
        str, Dict[str, Dict[str, List[EquitiesMovement]]]
    ]  # year → month → day


class Token(RFModel):
    access_token: str
    token_type: str
    email: str
    exp: datetime


class User(RFModel):
    accept_terms: bool = False
    created_at: datetime = datetime.now()
    document: str
    name: str
    lastname: Optional[str] = None
    password: str
    email: str
    phone: Optional[int] = None
    subscription: bool = False


class DarfExport(RFModel):
    year: str
    month: str
    value: str
    markets: List[str]  # B3::MARKET_TYPE
    url: str
