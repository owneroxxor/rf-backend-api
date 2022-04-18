import asyncio

from app.db.models import EquitiesMovement, get_model_attrs
from .enums import MARKET_TYPE
from datetime import datetime, date
from aiohttp import ClientSession
import json
import posixpath
import pandas as pd
from collections import OrderedDict
from typing import Collection, OrderedDict, Any, Dict, List, Optional, Tuple
from app.log import get_logger
from .exceptions import PaginatorException, MovementsException

log = get_logger(__name__)

B3_BASE_URL: str = "https://xxxxxxxxx/api/b3i/"
API_VERSION: str = "v1"


class B3:
    def __init__(self, base_url=B3_BASE_URL, auth=None, loop=None):
        """Initialise the class."""
        self._loop = loop or asyncio.get_event_loop()
        self._base_url = base_url
        self._auth = auth
        self._session = ClientSession(loop=self._loop)

    async def movements(
        self,
        market_type: MARKET_TYPE,
        document: str,
        start_date: date = None,
        end_date: date = None,
    ) -> Dict[int, Any]:
        try:
            path: OrderedDict[str, Any] = OrderedDict(
                endpoint="movement",
                version=API_VERSION,
                market_type=market_type,
                document=document,
                reference_start_date=start_date,
                reference_end_date=end_date,
            )
            movements: List[dict] = []
            pages = await self._paginator(method="GET", path=path)
            if pages is None:
                raise
            pages = movements.extend(
                p[f'{path["market_type"].capitalize()}Period'][
                    f'{path["market_type"]}{path["endpoint"].capitalize()}List'
                ]
                for p in pages
            )
            df = pd.DataFrame(pages)
            df.rename(
                columns=dict(list(zip(df.columns.values.tolist(), get_model_attrs(EquitiesMovement))))
            )
            df['year'] = df.reference_date.apply(lambda d: int(d.split('-')[0]))
            df['month'] = df.reference_date.apply(lambda d: int(d.split('-')[1]))
            # df = df.set_index(['year', 'month']).to_dict('index', into=OrderedDict)
            return df.groupby('year').apply(lambda year: dict(year.groupby('month').apply(lambda month: month.to_dict('records')))).to_dict(into=OrderedDict)
        except Exception as e:
            log.exception(
                "Got an exception when fetching movements",
                extra=dict(
                    path=path,
                    market_type=market_type,
                    document=document,
                    start_date=start_date,
                    end_date=end_date,
                ),
            )
            raise MovementsException from e

    async def _request(self, *, method, data=None, path=None, params=None):
        """Perform a request to the B3 API."""
        url = posixpath.join(self._base_url, path) if path else self._base_url
        data = json.dumps(data) if data else None
        async with self._session.request(method, url, data=data, params=params) as resp:
            assert resp.status == 200
            return await resp.json()

    async def _paginator(
        self, *, method, data=None, path=None, params=None
    ) -> Optional[List[dict]]:
        """Perform parallel requests to the B3 API, fetching all pages of a request."""
        try:
            page_param: Dict[str, int] = lambda pg: dict(pageNumber=pg)  # noqa
            params.update(page_param(1))

            fixed_kw: OrderedDict[str, Any] = OrderedDict(
                method=method, data=data, path=path.values()
            )

            resp = await self._request(**fixed_kw, params=params)
            pages_total: int = resp["Pagination"][0]["numberOfPages"]
            pending: Collection[asyncio.Future] = [
                self._request(
                    **fixed_kw, params=params.update(page_param(pg)) or params
                )
                for pg in range(1, pages_total + 1)
            ]

            pages = List[dict]

            while pending:
                done, pending = asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                for d in done:
                    pages.append(d.result())
        except Exception as e:
            log.exception(
                "Got an exception in paginator",
                extra=dict(method=method, data=data, path=path, params=params),
            )
            raise PaginatorException from e


B3_client: B3 = B3()
