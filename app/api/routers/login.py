from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.exceptions import PasswordMismatch, UserNotFound
from app.models import Token, User
from app.security import issue_jwt_token
from config import cfg
from db import DB_client
from log import get_logger

log = get_logger(__name__)

router = APIRouter()


@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate with the API",
    description="Returns a JWT with expiration.",
    tags=["Authentication"],
)
async def token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Returns a JWT token with expiration."""
    try:
        user: User = await authenticate_user(form_data.username, form_data.password)
    except UserNotFound:
        raise HTTPException(
            status_code=401, detail=f'User email "{form_data.username}" not found'
        )
    except PasswordMismatch:
        raise HTTPException(
            status_code=400,
            detail=f'Password given for "{form_data.username}" is incorrect',
        )
    except Exception:
        log.exception("Exception when authenticating user")
        raise HTTPException(
            status_code=500, detail="Unable to authenticate user right now"
        )
    return issue_jwt_token(
        expiry_delta=timedelta(minutes=cfg.token_expiration_minutes), email=user.email
    )


async def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates a user with given email and password or raise.

    :param email: user email
    :param password: user password
    :raises: UserNotFound, PasswordDontMatch
    """
    user: User = await DB_client.get_user(email)
    if not user:
        raise UserNotFound
    if user.password != password:
        raise PasswordMismatch
    return user
