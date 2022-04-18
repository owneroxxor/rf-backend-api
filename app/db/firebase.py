from typing import Optional
from aiofirebase import FirebaseHTTP
from config import cfg
from app.log import get_logger
from .models import User, Movements, EquitiesMovement
from app.exceptions import DatabaseException
from typing import Dict
from b3.enums import MARKET_TYPE


log = get_logger(__name__)

_fb: FirebaseHTTP = FirebaseHTTP(cfg.firebase_address)


def wrap_exceptions(fn):
    """Decorator to log exceptions and return None if a DB procedure has failed."""

    async def wrapper(*args, **kw):
        try:
            return await fn(*args, **kw)
        except TypeError:
            log.info(f"Not found: {fn.__name__}", extra=dict(args=args, **kw))
            return None
        except Exception as e:
            log.exception(f"Exception when executing Firebase API method: {fn.__name__}")
            raise DatabaseException from e
    return wrapper


@wrap_exceptions
async def get_user(email: str) -> Optional[User]:
    params = dict(orderBy="email", equalTo=email)
    return User(await _fb.get(path="users", params=params))

@wrap_exceptions
async def set_movements(user: User, movements: Movements):
    mvmts: Dict[str, dict] = {user.document: {movements.market_type: movements.movements}}
    return await _fb.put(value=mvmts, path="movements")  

@wrap_exceptions
async def get_movements(user: User, market_type: MARKET_TYPE = None):
  return await _fb.get(path=f"movements/{user.document}/{market_type if market_type else ''}")  

@wrap_exceptions
async def write_user(user: User) -> Optional[str]:
    return await _fb.put(value=user.dict(), path="users")
