import asyncio
from datetime import date
from typing import Dict, List, Optional, Union

import aiohttp
import pandas as pd
from aiofirebase import FirebaseHTTP

from app.exceptions import DatabaseException
from app.models import Movements, User
from b3 import MARKET_TYPE
from log import get_logger
from config import cfg

log = get_logger(__name__)


class FirebaseDB(FirebaseHTTP):
    def __init__(self, base_url: str, auth_token: str, loop=None):
        self._base_url: str = base_url
        self._auth_token: str = auth_token
        self._loop = loop or asyncio.get_event_loop()

    @property
    def _sess(self) -> aiohttp.ClientSession:
        return getattr(self, "_session")

    @property
    def is_started(self) -> bool:
        if self._sess:
            return self._sess.closed
        return False

    async def start(self) -> None:
        super().__init__(self._base_url, auth=self._auth_token, loop=self._loop)

    async def stop(self) -> None:
        if self.is_started:
            if not self._sess.closed:
                await self._sess.close()

    async def _request(self, *args, **kw):
        auth_param: Dict = dict(auth=self._auth)
        print(f"firebase:\nargs: {args}, kw: {kw}")
        kw["params"] = kw.get("params") or auth_param
        kw["params"].update(auth_param)
        if not self.is_started:
            await self.start()
        return await super()._request(*args, **kw)

    def wrap_exceptions(fn):
        """Decorator to log exceptions and raise a DB exception if something bad happened."""

        async def wrapper(*args, **kw):
            try:
                return await fn(*args, **kw)
            except Exception as e:
                log.exception(
                    f"Exception when executing Firebase API method: {fn.__name__}"
                )
                raise DatabaseException from e

        return wrapper

    @wrap_exceptions
    async def get_user(self, email: str) -> Optional[User]:
        params = quote(orderBy="email", equalTo=email)
        resp = await self.get(path="users", params=params)
        if resp:
            return User(**list(resp.values())[0])
        else:
            return None

    @wrap_exceptions
    async def set_movements(self, movements: List[Movements]):
        mvmts = {m.path: m.movements for m in movements}
        await self.patch(value=mvmts, path=f"movements")

    @wrap_exceptions
    async def get_movements(
        self,
        user: User,
        start_date: str,
        end_date: str,
        market_type: Union[List[str], str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Get movements from database.

        Will return movements from all market types available if no market_type was passed.
        """
        resp = await self.get(path=f"movements/{user.document}")
        print(f"movements from firebase:\n{resp}")
        if market_type is None:
            market_type = [m.value for m in cfg.supported_markets]  # set all market types
        elif isinstance(market_type, str):
            market_type = [market_type]

        ret: Dict[str, pd.DataFrame] = dict()

        for mkt_type in market_type:
            df = pd.DataFrame.from_dict(
                {
                    (int(yr), int(mo), int(day)): m
                    for yr in resp.get(mkt_type, {}).keys()
                    for mo in resp[mkt_type][yr].keys()
                    for day, movements in resp[mkt_type][yr][mo].items()
                    for m in movements
                    if m["reference_date"] >= start_date
                    and m["reference_date"] <= end_date
                },
                orient="index",
            )
            df.index.rename(["year", "month", "day"], inplace=True)
            print(f'df:"\n{df.to_string()}\n')
            ret[mkt_type] = df

        return ret

    @wrap_exceptions
    async def write_user(self, user: User) -> Optional[str]:
        return await self.put(value=user.dict(), path="users")


# -------- helpers ------
def quote(*args, **kw):
    return {k: f'"{v}"' for k, v in kw.items()}
