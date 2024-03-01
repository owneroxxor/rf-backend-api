class RFBaseException(Exception):
    """Base exception class for the RF-Backend-API"""

    pass


class UserNotFound(RFBaseException):
    pass


class PasswordMismatch(RFBaseException):
    pass


class ConnectionError(RFBaseException):
    pass


class DatabaseException(RFBaseException):
    pass
