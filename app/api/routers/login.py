from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.exceptions import HTTPException
from app.log import get_logger
from app.security import issue_jwt_token, JWTBearer
from datetime import timedelta
from typing import Dict, Any, Optional
from db.firebase import get_user
from db.models import Token, User
from app.exceptions import UserNotFound, PasswordDontMatch, ConnectionError

TOKEN_EXPIRY_MINUTES = 60

log = get_logger(__name__)

router = APIRouter()


@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate with the API",
    description="Returns a JWT with expiration.",
    tags=["login", "authentication", "auth", "JWT"],
)
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = await authenticate_user(form_data.username, form_data.password)
    except UserNotFound:
        raise HTTPException(
            status_code=401, detail=f'User email "{form_data.username}" not found'
        )
    except PasswordDontMatch:
        raise HTTPException(
            status_code=400,
            detail=f'Password given for "{form_data.username}" is incorrect',
        )
    except ConnectionError:
        raise HTTPException(
            status_code=500, detail="Unable to authenticate user right now"
        )
    return dict(
        access_token=issue_jwt_token(
            email=user.email, expiry_delta=timedelta(minutes=TOKEN_EXPIRY_MINUTES)
        ),
        token_type="bearer",
    )


async def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates a user with given email and password or raise.

    :param email: user email
    :param password: user password
    :raises: UserNotFound, PasswordDontMatch
    """
    user: User = await get_user(email)
    if user is None:
        log.exception("Failed to authenticate user")
        raise ConnectionError
    if not user:
        raise UserNotFound
    if user.password != password:
        raise PasswordDontMatch
    return user


# @router.post(
#     "/login",
#     summary="Authenticate with the API",
#     description="Returns a JWT with expiration.",
#     tags=["login", "authentication", "auth", "JWT"],
# )
# async def login(email: str, password: str):
#     """User login authentication method.
#     :param email: user email
#     :param password: user password
#     :return: a valid JWT token if authenticated
#     """
#     try:
#         await authenticate_user(email, password)

#     headers = dict(
#         Token=issue_jwt_token(
#             email=email, expiry_delta=timedelta(minutes=TOKEN_EXPIRY_MINUTES)
#         )
#     )
#     return JSONResponse(content=dict(), headers=headers)
