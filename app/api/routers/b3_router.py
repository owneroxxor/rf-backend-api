from datetime import date, datetime, timedelta
from typing import Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.models import Message, UnauthorizedMessage, Movements, MovementsGrouped, User
from app.security import get_api_user
from b3 import B3_TIME_EDGE, MARKET_TYPE, B3_client
from b3.models import B3AuthUrl
from config import cfg
from db import DB_client
from log import get_logger
from app.exceptions import DatabaseException
from b3.exceptions import MovementsException, UnauthorizedClientAccess

log = get_logger(__name__)

router = APIRouter()


@router.post(
    "/authorize",
    response_model=B3AuthUrl,
    summary="Request B3 authorization page.",
    tags=["B3"],
    description=(
        "The response contains an URL to a login page which authorizes RF to use B3 API on client's behalf."
    ),
    responses={
        500: dict(model=Message, description="Internal Error."),
        200: dict(model=B3AuthUrl, json={"url": "https://b3_authorization_form_url"}),
    },
)
async def authorize(user: User = Depends(get_api_user)):
    """Request B3 authorization page."""
    try:
        return B3AuthUrl(url=await B3_client.authorize())
    except Exception as e:
        msg = "Failed to retrieve B3 authorization page"
        log.exception(msg)
        raise JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=Message(msg=msg).dict(),
        ) from e


@router.get(
    "/movements",
    summary="Get the user movements.",
    description="Return a JSON with the movements.",
    tags=["B3"],
    responses={
        500: dict(model=Message, description="Internal Error."),
        401: dict(model=Message, description="Unauthorized to access B3 API on participants\' behalf."),
        400: dict(model=Message, description="Bad request."),
        200: dict(
            model=MovementsGrouped,
            description="Movements for the market type and period of the user.",
            content={
                "application/json": {
                    "example": {
                        "market_type": "equities",
                        "document": "04781722903",
                        "movements": {
                            "2018": {
                                "09": {
                                    "02": [
                                        {
                                            "reference_date": "2018-09-02",
                                            "product_category": "XXXXX",
                                            "product_type_name": "XXXXX",
                                            "movement_type": "Compra",
                                            "operation_type": "Crédito",
                                            "ticker_symbol": "XXXXX",
                                            "corporation_name": "XXXXXX",
                                            "participant_name": "XXXXX",
                                            "participant_document_number": "88888888888",
                                            "equities_quantity": 15,
                                            "unit_price": "7.90",
                                            "operation_value": "118.50",
                                        }
                                    ]
                                }
                            }
                        },
                    }
                }
            },
        ),
    },
)
async def get_movements(
    user: User = Depends(get_api_user),
    market_type: str = Query(...),
    start_date: date = Query(B3_TIME_EDGE()),
    end_date: date = Query(date.today()),
) -> Movements:
    """User movements."""
    # assert input constraints
    if market_type not in cfg.supported_markets:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=Message(msg="Invalid/Unsupported market type").dict(),
        )
    # assert start_date param
    if str(start_date) < str(B3_TIME_EDGE()):
        start_date = B3_TIME_EDGE()
    elif str(start_date) > str(date.today()):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=Message(msg="start_date is bigger than today\'s date").dict(),
        )
    # assert end_date param
    if str(end_date) > str(date.today()):
        end_date = date.today()
    if str(end_date) < str(start_date):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=Message(msg="end_date is lower than start_date\'s date").dict(),
        )

    # check local data available
    try:
        local_data: Dict[str, pd.DataFrame] = await DB_client.get_movements(
            user,
            market_type=market_type,
            start_date=str(start_date),
            end_date=str(end_date),
        )
    except DatabaseException as e:
        log.error(
            'Failed to fetch movements from DB',
            extra=dict(
                error=str(e),
                user=user.document,
                market_type=market_type,
                start_date=start_date,
                end_date=end_date,
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=Message(msg="Failed to retrieve movements").dict(),
        )

    # get the latest date available in local storage
    latest_local_date: str = str(B3_TIME_EDGE())
    if not local_data[market_type].empty:
        latest_local_date = _get_latest_date_from_movements(local_data[market_type])

    # if data is up till today, return it, otherwise we may have new data available on B3
    external_data: pd.DataFrame = pd.DataFrame()
    if latest_local_date < str(date.today()):
        try:
            external_data: pd.DataFrame = await B3_client.movements(
                market_type=market_type,
                document=user.document,
                start_date=str(
                    datetime.strptime(latest_local_date, "%Y-%m-%d") + timedelta(1)
                ),
            )
        except (UnauthorizedClientAccess, MovementsException) as e:
            log.error(
                "Failed to fetch movements from B3",
                extra=dict(
                    error=str(e),
                    user=user.document,
                    market_type=market_type,
                    start_date=start_date,
                    end_date=end_date,
                ),
            )
            if isinstance(e, UnauthorizedClientAccess):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=UnauthorizedMessage().dict(),
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content=Message(msg="Failed to retrieve movements").dict(),
                )

    # join local data with B3 data
    if not local_data[market_type].empty:
        if not external_data.empty:
            local_data[market_type] = pd.concat(
                [local_data[market_type], external_data]
            )
            # store the new collected external data
            await DB_client.set_movements(
                movements=_dict_to_movements_list(
                    document=user.document,
                    market_type=market_type,
                    movements=_df_to_movements_dict(external_data),
                )
            )
    grp = MovementsGrouped(
        document=user.document,
        market_type=market_type,
        movements=_df_to_movements_dict(local_data[market_type]),
    )
    print(f"grp: \n{grp}\n")
    return grp


#---------------- helpers ----------------
def _get_latest_date_from_movements(df: pd.DataFrame) -> str:
    return "-".join(
        str(df.index.get_level_values(idx).max()).zfill(2) for idx in df.index.names
    )

def _dict_to_movements_list(
    document: str, market_type: str, movements: dict
) -> List[Movements]:
    return [
        Movements(
            document=document,
            market_type=market_type,
            year=year,
            month=month,
            day=day,
            movements=mvmts,
        )
        for year, year_data in movements.items()
        for month, month_data in year_data.items()
        for day, mvmts in month_data.items()
    ]

def _df_to_movements_dict(df: pd.DataFrame) -> dict:
    """Will convert a pandas DataFrame with movements data to a nested dict of `Movements`."""
    df.reset_index(inplace=True)
    df["year"] = df.year.apply(str)
    df["month"] = df.month.apply(str).str.zfill(2)
    df["day"] = df.day.apply(str).str.zfill(2)
    print(f"new df:\n{df.to_string()}\n")
    di = (
        df.groupby("year")
        .apply(
            lambda year: dict(
                year.groupby("month").apply(
                    lambda month: dict(
                        month.groupby("day").apply(
                            lambda day: day.drop(
                                list(df.index.names), axis=1, errors="ignore"
                            ).to_dict("records")
                        )
                    )
                )
            )
        )
        .to_dict(into=dict)
    )
    print(f"df: {di}")
    return di
