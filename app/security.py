from app.log import get_logger

import jwt
from fastapi import Depends, status
from jwt.exceptions import ExpiredSignatureError
from fastapi import HTTPException
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes,
)
from db.firebase import get_user
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from db.models import User

log = get_logger()

_SIG_KEY: str = open(".ssh/id_rsa").read()
_TOKEN_EXPIRY_SECONDS = 3600

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_api_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))):
    payload = verify_jwt(token)
    email: str = payload.get("email")
    if email is None:
        raise CREDENTIALS_EXCEPTION
    user = await get_user(email=email)
    if user is None:
        raise CREDENTIALS_EXCEPTION
    return user


def issue_jwt_token(expiry_delta: timedelta = None, **data):
    """Issue a new JWT with expiration."""
    payload: Dict[str, Any] = dict(
        **data,
    ).update(dict(exp=datetime.utcnow() + expiry_delta) if expiry_delta else {})
    return jwt.encode(payload=payload, key=_SIG_KEY)


def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, key=_SIG_KEY, algorithms=["RS256"], verify_exp=True)
    except ExpiredSignatureError:
        log.info("Expired JWT token submitted", extra=dict(token=token))
    except Exception:
        log.exception("Invalid JWT token submitted", extra=dict(token=token))
