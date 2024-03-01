from typing import List
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from datetime import date
from app.models import Message, User
from app.security import get_api_user
from log import get_logger
from config import cfg
from calc import generate_darf

log = get_logger(__name__)

router = APIRouter()


@router.get(
    "/darf",
    response_model=Darf,
    summary="Return the darf data.",
    description="Return a JSON with the darf data.",
    responses={
        500: dict(model=Message, description="Internal Error."),
        404: dict(model=Message, description="The item was not found."),
        200: dict(
            model=Darf,
            description="Darf for the market types and period.",
            content={
                "application/json": {
                    "example": {
                        "year": "2021",
                        "month": "03",
                        "value": "1097.16",
                        "markets": ["equities", "future", "options"],
                        "url": "https://darf.url.com/darf-12345.pdf"
                    }
                }
            },
        )
    },
)
async def darf(
    user: User = Depends(get_api_user),
    markets: List[str] = Query(...),
    year: int = Query(...),
    month: int = Query(...),
):
    """Generate darf."""
    # assert input constraints
    if not set(markets).issubset(cfg.supported_markets):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=Message(msg="Invalid/Unsupported market type passed").dict(),
        )
    # assert the year param
    if year > date.today().year:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=Message(msg="Invalid year passed, the year is in the future").dict(),
        )
    # assert the month param
    if month < 1 or month > 12:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=Message(msg="Invalid month passed").dict(),
        )
    try:
        return await generate_darf(markets=markets, year=year, month=month, user=user)
    except Exception as e:
        log.exception(e)