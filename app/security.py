from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import ExpiredSignatureError

from app.models import Token, User
from db import DB_client
from log import get_logger

log = get_logger()

_SIG_KEY: str = open(".rsa/id_rsa").read()

CREDENTIALS_EXCEPTION = lambda reason: HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail=f"Could not validate credentials: {reason}",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_api_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))):
    """Verify the user."""
    try:
        payload = verify_jwt(token)
    except Exception as e:
        if isinstance(e, ExpiredSignatureError):
            raise CREDENTIALS_EXCEPTION("token has expired")
        else:
            raise CREDENTIALS_EXCEPTION("invalid token")
    email: str = payload.get("email")
    if email is None:
        raise CREDENTIALS_EXCEPTION("invalid email")
    user: User = await DB_client.get_user(email=email)
    if user is None:
        raise CREDENTIALS_EXCEPTION("invalid user")
    return user


def issue_jwt_token(
    expiry_delta: timedelta = None, token_type="bearer", **data
) -> Token:
    """Issue a new JWT with expiration."""
    payload: Dict[str, Any] = dict(**data)
    payload.update(dict(exp=datetime.utcnow() + expiry_delta) if expiry_delta else {})
    return Token(
        access_token=jwt.encode(payload=payload, key=_SIG_KEY),
        token_type=token_type,
        email=payload.get("email"),
        exp=payload.get("exp"),
    )


def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Verify the JWT token."""
    try:
        return jwt.decode(token, key=_SIG_KEY, algorithms=["HS256"], verify_exp=True)
    except ExpiredSignatureError as e:
        log.info("Expired JWT token submitted", extra=dict(token=token))
        raise e
    except Exception as e:
        log.exception("Invalid JWT token submitted", extra=dict(token=token))
        raise e
