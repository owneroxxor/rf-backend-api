from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, List
from pydantic import BaseModel


def get_model_attrs(model: BaseModel):
    """Return the attributes of a model."""
    return list(model.__fields__.keys())


class Message(BaseModel):
    msg: str


class Movement(BaseModel):
    pass


class EquitiesMovement(Movement):
    reference_date: date
    product_category: str
    product_type_name: str
    movement_type: str
    operation_type: str
    ticker_symbol: str
    corporation_name: str
    participant_name: str
    equities_quantity: Decimal
    unit_price: Decimal
    operation_value: Decimal


class Movements(BaseModel):
    document: Optional[str]
    market_type: str
    timestamp: datetime = datetime.now()
    movements: Dict[str, Dict[int, Dict[int, List[Movement]]]]  # year → month


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    accept_terms: bool = False
    created_at: datetime = datetime.now()
    document: Optional[int] = None
    name: Optional[str] = None
    lastname: Optional[str] = None
    password: Optional[str] = None
    phone: Optional[int] = None
    subscription: Optional[bool] = False
