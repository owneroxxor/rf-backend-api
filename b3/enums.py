from enum import Enum, EnumMeta


class MetaEnum(EnumMeta):
    def __contains__(cls, item):
        try:
            cls(item)
        except ValueError:
            return False
        return True


class BaseEnum(Enum, metaclass=MetaEnum):
    ...


class MARKET_TYPE(BaseEnum):
    BOX = "box"
    FORWARD = "forward"
    FUTURE = "future"
    OPTIONS = "options"
    SWAP = "swap"
    FIXED_INCOME = "fixed-income"
    COE = "coe"
    EQUITIES = "equities"
    ETF = "etf"
    INTERNATIONAL_ETF = "international-etf"
    INVESTMENT_FUNDS = "investment-funds"
    SECURITIES_LENDING = "securities-lending"
    TREASURY_BONDS = "treasury-bonds"


class RESPONSE_CODE(BaseEnum):
    RESPONSE_CODE_NOT_AUTHORIZED_ACCESS = "422.02"
    RESPONSE_CODE_CPF_CNPJ_NOT_FOUND = "422.03"
    RESPONSE_CODE_TOO_MANY_REQUESTS = "429"
    RESPONSE_CODE_INTERNAL_SERVER_ERROR = "500"
