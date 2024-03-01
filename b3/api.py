import asyncio
import json
import os
import pathlib
import posixpath
import ssl
from collections import OrderedDict
from datetime import date
from typing import Any, Collection, Dict, List, OrderedDict, Union
from urllib.parse import urlencode

import aiohttp
import certifi
import pandas as pd
from aiohttp import ClientSession

from app.models import EquitiesMovement, Movement
from log import get_logger

from .exceptions import (
    InconsistentPaginatorData,
    MovementsException,
    PaginatorException,
    RequestException,
    TokenException,
    B3ResponseException,
    UnauthorizedClientAccess,
    raise_for_status
)
from .models import B3Credentials, Token

API_VERSION: str = "v2"
ROOT_DIR = pathlib.Path.cwd()
CERT_PATH = ROOT_DIR / ".rsa" / "certificate.cer"
CERT_PW = open(ROOT_DIR / ".rsa" / "pw").read()
KEY_PATH = ROOT_DIR / ".rsa" / "key.key"

log = get_logger(__name__)


class B3:
    def __init__(self, config: Dict, loop=None):
        """Initialise the class."""
        self._loop = loop or asyncio.get_event_loop()
        self._auth = B3Credentials(**config.get("auth"))
        self._token: Token = None
        self._token_url: str = config.get("token_url")
        self._token_scope: str = config.get("token_scope")
        self._base_url: str = config.get("base_url")
        self._auth_url: str = config.get("auth_url")
        self._api_path: Dict[str, str] = config.get("api_path")
        self._session: ClientSession = None

    @property
    def is_started(self):
        if self._session is not None:
            return not self._session.closed
        return False

    async def start(self) -> None:
        if not self.is_started:
            self._session = ClientSession(
                loop=self._loop, connector=_get_ssl_connector()
            )
        await self._get_token()

    async def stop(self) -> None:
        if self.is_started:
            if not self._session.closed:
                await self._session.close()

    async def health() -> None:
        ...

    async def authorize(self) -> str:
        """Authorize RF to use B3 APIs on behalf of one's account.

        :returns: return the auth form post URL for the client to login.
        """
        return self._auth_url

    async def _get_token(self) -> None:
        """Require oauth 2.0 token from B3 to execute API calls."""
        try:
            data: str = urlencode(
                dict(
                    grant_type="client_credentials",
                    client_id=self._auth.client_id,
                    client_secret=self._auth.client_secret,
                    scope=self._token_scope,
                )
            )
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            resp = await self._request(
                method="POST", url=self._token_url, data=data, headers=headers
            )
            self._token = Token(**resp)
        except Exception as e:
            log.exception(
                "Got an exception when fetching B3 access token",
                extra=dict(url=self._token_url, data=data),
            )
            raise TokenException from e

    async def movements(
        self,
        market_type: str,
        document: str,
        start_date: str = None,
        end_date: str = str(date.today()),
    ) -> pd.DataFrame:
        try:
            path: OrderedDict[str, Any] = OrderedDict(
                endpoint="movement",
                version=API_VERSION,
                market_type=market_type,
                investors="investors",
                document=document,
            )
            params: Dict[str, Any] = dict(
                referenceStartDate=start_date, referenceEndDate=end_date
            )
            movements: List[dict] = []
            pages = await self._paginator(method="GET", path=path, params=params)

            for p in pages:
                if not "data" in p:
                    raise_for_status(p['code'])
                    raise InconsistentPaginatorData(page=p)
                movements.extend(
                    p["data"][f'{path["market_type"].value}Periods'][
                        f'{path["market_type"].value}Movements'
                    ]
                )

            df = pd.DataFrame(pages)
            df.rename(
                columns=dict(
                    list(zip(df.columns.values.tolist(), EquitiesMovement.attrs))
                )
            )
            df["year"] = df.reference_date.apply(lambda d: int(d.split("-")[0]))
            df["month"] = df.reference_date.apply(lambda d: int(d.split("-")[1]))
            df["day"] = df.reference_date.apply(lambda d: int(d.split("-")[2]))
            df.set_index(["year", "month", "day"], inplace=True)
            return df

        except Exception as e:
            if isinstance(e, InconsistentPaginatorData):
                log.error('Received inconsistent paginator data', extra=dict(error=str(e), page=e.page))
            elif isinstance(e, B3ResponseException):
                log.error('Received bad response from B3', extra=dict(error=str(e)))
                if isinstance(e, UnauthorizedClientAccess):
                    raise e
            else:
                log.exception(
                    "Got an exception when fetching B3 movements",
                    extra=dict(
                        error=str(e),
                        path=path,
                        market_type=market_type,
                        document=document,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                )
            raise MovementsException from e

    async def _request(
        self, *, method, url=None, data=None, path=None, params=None, headers=None
    ) -> Dict:
        """Perform a request to the B3 API.

        :raises RequestException: got a request exception
        """
        if not self.is_started:
            await self.start()
        url = url or self._base_url
        url = posixpath.join(url, path) if path else url
        data = (
            json.dumps(data)
            if isinstance(data, dict)
            else data
            if isinstance(data, str)
            else None
        )
        headers = (
            {"Authorization": f"{self._token.token_type} {self._token.access_token}"}
            if self._token
            else headers
        )

        try:
            async with self._session.request(
                method, url, data=data, params=params, headers=headers
            ) as resp:
                # data = body, params = query
                try:
                    ret = await resp.json()
                except:
                    ret = dict(
                        code=resp.status, message=await resp.text() or "no message"
                    )
                if resp.status != 200:
                    log.warning(f"Received bad status", extra=dict(response=ret))
                return ret
        except Exception as e:
            log.exception(
                f"Got a request exception",
                extra=dict(
                    method=method, url=url, data=data, params=params, headers=headers
                ),
            )
            raise RequestException from e

    async def _paginator(
        self, *, method, data=None, path=None, params={}
    ) -> List[Dict]:
        """Perform parallel requests to the B3 API, fetching all pages of a request.

        :raises PaginatorException: failed to paginate
        """
        try:
            page_param: Dict[str, int] = lambda pg: dict(page=pg)  # noqa
            params.update(page_param(1))
            fixed_kw: OrderedDict[str, Any] = OrderedDict(
                method=method, data=data, path=os.path.join(*path.values())
            )
            resp = await self._request(**fixed_kw, params=params)

            if not "links" in resp:
                return [resp]

            pages_total: int = resp["links"]["last"].split("=")[-1]
            pending: Collection[asyncio.Future] = [
                self._request(
                    **fixed_kw, params=params.update(page_param(pg)) or params
                )
                for pg in range(1, pages_total + 1)
            ]

            pages = List[Union[str, dict]]

            while pending:
                done, pending = asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                for d in done:
                    pages.append(d.result())

            return pages
        except Exception as e:
            log.exception(
                "Got an exception in paginator",
                extra=dict(**fixed_kw, params=params),
            )
            raise PaginatorException from e

def _get_ssl_connector() -> aiohttp.TCPConnector:
    ssl_ctx = ssl.create_default_context(
        ssl.Purpose.CLIENT_AUTH, cafile=certifi.where()
    )
    ssl_ctx.load_cert_chain(CERT_PATH, KEY_PATH, CERT_PW)
    return aiohttp.TCPConnector(ssl=ssl_ctx)