from .enums import RESPONSE_CODE

class B3BaseException(Exception):
    """Base B3 exception class."""
    @classmethod
    def __str__(cls):
        return cls.__name__

class B3ResponseException(B3BaseException):
    """Base response exception class."""

    ...

class RequestException(B3BaseException):
    ...


class PaginatorException(B3BaseException):
    ...


class MovementsException(B3BaseException):
    ...


class TokenException(B3BaseException):
    ...


class AuthException(B3BaseException):
    ...


class InconsistentPaginatorData(B3BaseException):
    def __init__(self, page: dict):
        self.page = page
        super().__init__()

class UnauthorizedClientAccess(B3ResponseException):
    ...


class UnknownStatusReceived(B3ResponseException):
    def __init__(self, status: str):
        self.status = status
        super().__init__()
    def __str__(self):
        return f'{self.__class__.__name__}:{self.status}'


class TooManyRequests(B3ResponseException):
    ...


def raise_for_status(status: str):
    """Raise status for http codes received from B3."""
    try:
        code = RESPONSE_CODE(status)
    except ValueError:
        raise UnknownStatusReceived(status=status)
    if code == RESPONSE_CODE.RESPONSE_CODE_NOT_AUTHORIZED_ACCESS:
        raise UnauthorizedClientAccess
    if code == RESPONSE_CODE.RESPONSE_CODE_TOO_MANY_REQUESTS:
        raise TooManyRequests