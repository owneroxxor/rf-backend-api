from calendar import month
from attrs import exceptions
from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasicCredentials
from fastapi.exceptions import HTTPException
from app.log import get_logger
from app.security import get_api_user
from datetime import timedelta, date
from typing import Dict, Any, Optional
from db.firebase import get_user, set_movements
from db.models import Movements, User, Message
from app.b3 import B3_client
from b3.enums import MARKET_TYPE
import pandas as pd

log = get_logger(__name__)

router = APIRouter()

B3_TIME_EDGE = lambda: date.today() - timedelta(
    days=558
)  # 18 months ago is the B3 storing edge


@router.get(
    '/movements',
    response_model=Movements,
    summary='Get the user movements',
    description='Return a JSON with the movements.',
    responses={
        500: dict(model=Message, description='Internal Error.'),
        404: dict(model=Message, description='The item was not found.'),
        200: dict(
            description='Movements for the market type and period.',
            content=dict(json={"example": {"id": "bar", "value": "The bar tenders"}})
        ),
    },
)
async def movements(
    user: User = Depends(get_api_user),
    market_type: str = Query(...),
    start_date: date = Query(B3_TIME_EDGE()),
    end_date: date = Query(date.today()),
):
    """User movements."""
    if market_type not in MARKET_TYPE:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=Message(msg='Invalid market type').dict(),
        )
    try:
        mvts: Dict[int, Any] = B3_client.movements(
            market_type=MARKET_TYPE.EQUITIES,
            document=user.document,
            start_date=start_date,
            end_date=end_date,
        )
        return Movements(market_type=market_type, document=user.document, movements=mvts)
    except Exception:
        log.exception(
            'Got an exception when fetching B3 movements',
            extra=dict(
                user=user.document,
                market_type=market_type,
                start_date=start_date,
                end_date=end_date,
            ),
        )
